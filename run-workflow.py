import logging
import os
import re
import sys
import tempfile
import uuid
from typing import Any

import boto3
import environ
import requests
import sh

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "WARNING"),
    stream=sys.stdout,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logging.getLogger("sh").setLevel(logging.INFO)


@environ.config(prefix="")
class AppConfig:
    @environ.config
    class S3:
        access_key_id: str = environ.var()
        secret_access_key: str = environ.var()
        endpoint_url: str = environ.var(default="https://storage.googleapis.com")
        region_name: str = environ.var(default="europe-west1")

    s3: S3 = environ.group(S3)
    app_venv = environ.var()
    file_url: str = environ.var()
    analysis_variable: str = environ.var()
    output_bucket: str = environ.var()
    output_key: str = environ.var()

    @property
    def python_interpreter(self) -> str:
        return os.path.join(self.app_venv, "bin", "python")

    @property
    def s3_client(self) -> Any:
        s3_client = boto3.client(
            "s3",
            endpoint_url=self.s3.endpoint_url,
            region_name=self.s3.region_name,
            aws_access_key_id=self.s3.access_key_id,
            aws_secret_access_key=self.s3.secret_access_key,
        )

        return s3_client


def ensure_bucket_exists(s3_client: Any, bucket_name: str) -> None:
    s3_client.head_bucket(Bucket=bucket_name)
    logging.debug("Bucket '%s' already exists", bucket_name)


def upload_file_to_s3(
    s3_client: Any, file_path: str, bucket_name: str, s3_key: str
) -> None:
    logging.info("Uploading file %s to %s/%s", file_path, bucket_name, s3_key)
    s3_client.upload_file(file_path, bucket_name, s3_key)
    logging.info("File %s uploaded to %s/%s", file_path, bucket_name, s3_key)


def main():
    cfg = environ.to_config(AppConfig)

    ensure_bucket_exists(s3_client=cfg.s3_client, bucket_name=cfg.output_bucket)

    if re.compile(r"^https?://").match(cfg.file_url):
        input_file = os.path.join(
            tempfile.gettempdir(), "input-{}".format(uuid.uuid4().hex)
        )

        logging.info("Downloading file from %s", cfg.file_url)
        response = requests.get(cfg.file_url)

        with open(input_file, "wb") as fh:
            fh.write(response.content)
    else:
        input_file = cfg.file_url

    temp_output_file = os.path.join(
        tempfile.gettempdir(), "output-{}.html".format(uuid.uuid4().hex)
    )

    cmd_args = [
        "-m",
        "src.cmp.main",
        input_file,
        cfg.analysis_variable,
        temp_output_file,
    ]

    logging.info("Running command: %s", " ".join([cfg.python_interpreter, *cmd_args]))

    for line in sh.Command(cfg.python_interpreter)(*cmd_args, _iter=True):
        logging.info("%s", line.strip())

    with open(temp_output_file, "r") as fh:
        logging.debug("Output file (%s):\n%s\n[...]", temp_output_file, fh.read()[:250])

    upload_file_to_s3(
        s3_client=cfg.s3_client,
        file_path=temp_output_file,
        bucket_name=cfg.output_bucket,
        s3_key=cfg.output_key,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        logging.error("An error occurred: %s", ex)
        raise Exception("Workflow error") from ex
