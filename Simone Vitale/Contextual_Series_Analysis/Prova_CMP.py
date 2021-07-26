#%matplotlib inline

# Imports
import numpy as np
import matplotlib.pyplot as plt

from distancematrix.generator.znorm_euclidean import ZNormEuclidean  # Generators live in the generator package
from distancematrix.consumer.matrix_profile_lr import MatrixProfileLR  # Consumers live in the consumer package
from distancematrix.calculator import AnytimeCalculator

# Create a one-dimensional series with 2 artefacts
data = np.array([
    np.sin(np.linspace(0,20,1000))*0.2 + np.random.rand(1000) * 0.1
])

data[0, 100:120] += np.linspace(0.1, 0.5, 20)
data[0, 720:740] += np.linspace(0.1, 0.5, 20)

plt.plot(data[0])
plt.show()

# Setup generator, consumer and calculator
m = 100  # Subsequence length

calc = AnytimeCalculator(m, data)  # One series passed => self-join

gen_0 = calc.add_generator(0, ZNormEuclidean(noise_std=0.))  # Generator 0 works on channel 0
cons_0 = calc.add_consumer([0], MatrixProfileLR())  # Consumer 0 works on generator 0

# Calculate
calc.calculate_diagonals(print_progress=True, partial=1.)

# Admire the results
min_idx = np.argmin(cons_0.matrix_profile())
match_idx = cons_0.profile_index()[min_idx]

plt.figure(figsize=(15,5))

plt.subplot(2, 1, 1)
plt.title("Data")
plt.plot(data[0])
plt.plot(range(min_idx, min_idx+m), data[0, min_idx : min_idx + m], label = "Motif")
plt.plot(range(match_idx, match_idx+m), data[0, match_idx:match_idx+m], label="Best match")
plt.gca().set_xlim((0, data.shape[1]))
plt.legend()

plt.subplot(2, 1, 2)
plt.title("Matrix Profile")
plt.plot(cons_0.matrix_profile())
plt.vlines(min_idx, 0, 10, label="Minimum")
plt.gca().set_xlim((0, data.shape[1]))
plt.legend()


plt.show()