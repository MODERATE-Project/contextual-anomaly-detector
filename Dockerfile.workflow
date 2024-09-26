ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements-workflow.txt /tmp/requirements-workflow.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements-workflow.txt

ARG UID=10001
ARG GROUPNAME=appuser
ARG USERNAME=appuser

RUN groupadd -r ${GROUPNAME} && \
    useradd --create-home --no-log-init --uid "${UID}" -r -g ${GROUPNAME} ${USERNAME}

USER ${USERNAME}

RUN python -m pip install poetry

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV APP_PATH=/app
ENV APP_VENV=${APP_PATH}/.venv

WORKDIR ${APP_PATH}
COPY --chown=${USERNAME}:${GROUPNAME} . .
RUN poetry install --only main --no-interaction --no-ansi

CMD ["python", "/app/run-workflow.py"]