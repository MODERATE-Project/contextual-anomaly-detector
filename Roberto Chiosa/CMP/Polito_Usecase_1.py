import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import pandas as pd
import itertools

from distancematrix.calculator import AnytimeCalculator
from distancematrix.generator import ZNormEuclidean, Euclidean
from distancematrix.consumer import MatrixProfileLR, ContextualMatrixProfile
from distancematrix.consumer.contextmanager import GeneralStaticManager
from distancematrix.insights import highest_value_idxs

########################################################################################
# load dataset
data = pd.read_csv("Polito_Usecase/polito.csv", index_col='timestamp', parse_dates=True)

# print dataset main characteristics
print(' POLITO CASE STUDY\n',
      '*********************\n',
      'Electrical Load dataset from Substation C\n',
      '- From\t', data.index[0], '\n',
      '- To\t', data.index[len(data) - 1], '\n',
      '-', len(data), 'observations every 15 min\n',
      '- 96 \t observations per day\n',
      '- 4 \t observations per hour\n'
      )

# useful variables
dpi_resolution = 300
obs_per_day = 96
obs_per_hour = 4

# Visualise the data
plt.figure(figsize=(10, 3))
plt.subplot(2, 1, 1)
plt.title("Total Power (complete)")
plt.plot(data)
plt.ylabel("Power [kW]")

plt.subplot(2, 1, 2)
plt.title("Total Power (first two weeks)")
plt.plot(data.iloc[:4 * 24 * 7 * 2])
plt.ylabel("Power [kW]")

plt.gca().xaxis.set_major_locator(mdates.DayLocator([1, 8, 15]))
plt.gca().xaxis.set_minor_locator(mdates.DayLocator())
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

plt.grid(b=True, axis="x", which='both', color='black', linestyle=':')

position_x = 6  # position of day labels on x axis
position_y = 620  # position of day labels on y axis

# add day labels on plot
for i in range(14):
    timestamp = data.index[position_x + i * 96]
    plt.text(timestamp, position_y, timestamp.day_name()[:3])

plt.tight_layout()

# save figure to plot directories
plt.savefig("Polito_Usecase/polito.png", dpi=dpi_resolution, bbox_inches='tight')

########################################################################################
# Define configuration for the Contextual Matrix Profile calculation.

# time window length
m = 96 - 4 * 2  # 22 hours

# Each context starts between 0 and 2 AM, and lasts 22 hours
contexts = GeneralStaticManager([range(x * 96, (x * 96) + 4 * 2) for x in range(len(data) // 96)])

calc = AnytimeCalculator(m, data.values.T)

## Add generator as Znormalized Euclidean Distance (original)
# calc.add_generator(0, ZNormEuclidean())

# Add generator as Znormalized Euclidean Distance
calc.add_generator(0, Euclidean())

# We want to calculate CMP initialize element
cmp = calc.add_consumer([0], ContextualMatrixProfile(contexts))

# We want to calculate MP initialize element
mp = calc.add_consumer([0], MatrixProfileLR())

# Calculate Matrix Profile and Contextual Matrix Profile
calc.calculate_columns()

########################################################################################
# Visualise the CMP
# Note the very subtle color difference before and after 2014-08-31
date_labels = mdates.date2num(data.index[::48 * 2].values)

plt.figure(figsize=(10, 10))
extents = [date_labels[0], date_labels[-1], date_labels[0], date_labels[-1]]
plt.imshow(cmp.distance_matrix, extent=extents, cmap="viridis", origin="lower")
cbar = plt.colorbar()
plt.title("Contextual Matrix Profile\nNot Normalized Euclidean Distance\n")

# Label layout
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
plt.gca().yaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
plt.gca().xaxis.set_major_locator(mticker.MultipleLocator(14))
plt.gca().yaxis.set_major_locator(mticker.MultipleLocator(14))
plt.gcf().autofmt_xdate()
cbar.set_label("Distance")

plt.savefig("Polito_Usecase/polito_cmp1.png", dpi=dpi_resolution, bbox_inches='tight')

########################################################################################
# Create boolean arrays to indicate whether each day is a weekday/weekend/saturday/sunday

annotation_df = pd.read_csv("Polito_Usecase/polito_holiday.csv", index_col='timestamp', parse_dates=True)

holiday = np.array(annotation_df.T)[0]
saturdays = np.array(annotation_df.T)[1]
workingdays = np.array(annotation_df.T)[2]

day_labels = data.index[::96]

# Create weekday/weekend only CMP
holiday_cmp = cmp.distance_matrix[:, holiday][holiday, :]
holiday_cmp[holiday_cmp == np.inf] = 0
holiday_dates = data.index[::96].values[holiday]

saturday_cmp = cmp.distance_matrix[:, saturdays][saturdays, :]
saturday_cmp[saturday_cmp == np.inf] = 0
saturday_dates = data.index[::96].values[saturdays]

workingdays_cmp = cmp.distance_matrix[:, workingdays][workingdays, :]
workingdays_cmp[workingdays_cmp == np.inf] = 0
workingdays_dates = data.index[::96].values[workingdays]

# Calculate an anomaly score by summing the values (per type of day) across one axis and averaging
cmp_holiday_score = np.nansum(holiday_cmp, axis=1) / np.count_nonzero(holiday)
# cmp_holiday_score = cmp_holiday_score / np.max(cmp_holiday_score)

cmp_saturday_score = np.nansum(saturday_cmp, axis=1) / np.count_nonzero(saturdays)
# cmp_saturday_score = cmp_saturday_score / np.max(cmp_saturday_score)

cmp_workingdays_score = np.nansum(workingdays_cmp, axis=1) / np.count_nonzero(workingdays)
# cmp_workingdays_score = cmp_holiday_score / np.max(cmp_workingdays_score)

# Merge the scores for all types of day into one array
cmp_ad_score = np.zeros(len(cmp.distance_matrix))

cmp_ad_score[holiday] = cmp_holiday_score
cmp_ad_score[saturdays] = cmp_saturday_score
cmp_ad_score[workingdays] = cmp_workingdays_score

# Ordering of all days, from most to least anomalous
ad_order = np.argsort(cmp_ad_score)[::-1]

num_anomalies_to_show = 15

# Plot the anomaly scores and our considered threshold
plt.figure(figsize=(15, 3))
plt.title("Sorted Anomaly Scores")
plt.plot(cmp_ad_score[ad_order])
plt.ylabel("Anomaly Score")

plt.axvline(num_anomalies_to_show, ls=":", c="gray")
plt.xticks([0, 10, 20, 50, 100, 150])
plt.show()

# Plot the above figures together
plt.figure(figsize=(17, 2.5))
plt.subplot(1, 4, 1)
date_labels = mdates.date2num(holiday_dates)
extents = [date_labels[0], date_labels[-1], date_labels[0], date_labels[-1]]
plt.imshow(holiday_cmp,
           cmap="viridis",
           origin="lower",
           vmin=np.min(holiday_cmp),
           vmax=np.max(holiday_cmp),
           )
cbar = plt.colorbar()
plt.xlabel("Holiday Index")
# plt.yticks([0, 50, 100, 150])
plt.title("Power CMP (holiday only)")
cbar.set_label("Distance")

plt.subplot(1, 4, 2)
date_labels = mdates.date2num(saturday_dates)
extents = [date_labels[0], date_labels[-1], date_labels[0], date_labels[-1]]
plt.imshow(saturday_cmp,
           cmap="viridis",
           origin="lower",
           vmin=np.min(saturday_cmp),
           vmax=np.max(saturday_cmp),
           )
cbar = plt.colorbar()
plt.xlabel("Saturday Index")
# plt.yticks([0, 10, 20, 30])
plt.title("Power CMP (Saturday only)")
cbar.set_label("Distance")

plt.subplot(1, 4, 3)
date_labels = mdates.date2num(workingdays_dates)
extents = [date_labels[0], date_labels[-1], date_labels[0], date_labels[-1]]
plt.imshow(workingdays_cmp, cmap="viridis",
           origin="lower",
           vmin=np.min(workingdays_cmp),
           vmax=np.max(workingdays_cmp),
           )
cbar = plt.colorbar()
plt.xlabel("Working days Index")
# plt.yticks([0, 10, 20])
plt.title("Power CMP (Working days only)")
cbar.set_label("Distance")

plt.subplot(1, 4, 4)
plt.title("Sorted Anomaly Scores")
plt.plot(cmp_ad_score[ad_order])
plt.ylabel("Anomaly Score")

plt.axvline(10, ls=":", c="gray")
# plt.xticks([0, 18, 50, 100, 150, 200])

plt.savefig("Polito_Usecase/polito_cmp_detail1.png", dpi=dpi_resolution, bbox_inches='tight')

########################################################################################
# Visualise the top anomalies according to the CMP
fig, ax = plt.subplots(num_anomalies_to_show, 4, sharex=True, sharey=True, figsize=(10, 14),
                       gridspec_kw={'wspace': 0., 'hspace': 0.})

ax[0, 0].set_title("Anomaly vs all")
ax[0, 1].set_title("Anomaly vs holiday")
ax[0, 2].set_title("Anomaly vs saturdays")
ax[0, 3].set_title("Anomaly vs workingdays")

for i in range(num_anomalies_to_show):
    anomaly_index = ad_order[i]
    anomaly_range = range(96 * anomaly_index, 96 * (anomaly_index + 1))
    date = day_labels[anomaly_index]

    if holiday[anomaly_index] == True:
        # we are on holiday
        ls1 = "-"
        ls2 = ":"
        ls3 = ":"
        date_col = 1

    if saturdays[anomaly_index] == True:
        # we are on saturdays
        ls1 = ":"
        ls2 = "-"
        ls3 = ":"
        date_col = 2

    if workingdays[anomaly_index] == True:
        # we are on weekdays
        ls1 = ":"
        ls2 = ":"
        ls3 = "-"
        date_col = 3

    ax[i, 0].plot(data.values.reshape((-1, 96)).T, c="gray", alpha=0.07)
    ax[i, 0].plot(data.values[anomaly_range], c="red")

    ax[i, 1].plot(data.values.reshape((-1, 96))[holiday].T, c="gray", alpha=0.07)
    ax[i, 1].plot(data.values[anomaly_range], c="red", linestyle=ls1)

    ax[i, 2].plot(data.values.reshape((-1, 96))[saturdays].T, c="gray", alpha=0.07)
    ax[i, 2].plot(data.values[anomaly_range], c="red", linestyle=ls2)

    ax[i, 3].plot(data.values.reshape((-1, 96))[workingdays].T, c="gray", alpha=0.07)
    ax[i, 3].plot(data.values[anomaly_range], c="red", linestyle=ls3)

    ax[i, 0].text(0, 650, "CMP-Anomaly " + str(i + 1))
    ax[i, date_col].text(0, 650, date.day_name() + " " + str(date)[:10])

ax[0, 0].set_xticks(range(0, 97, 24))
ticklabels = ["{hour}:00".format(hour=(x // 4)) for x in range(0, 97, 24)]
ticklabels[-1] = ""
ax[0, 0].set_xticklabels(ticklabels)

plt.tight_layout()

ax[num_anomalies_to_show // 2, 0].set_ylabel("Power [kW]")
ax[num_anomalies_to_show - 1, 1].set_xlabel("Time of day")

plt.savefig("Polito_Usecase/polito_cmp_anomalies1.png", dpi=dpi_resolution, bbox_inches='tight')
