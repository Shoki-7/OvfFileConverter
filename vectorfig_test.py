import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import hsv_to_rgb


def get_rgb_colormap(array):
    """
    Given a 3D array with shape (nx, ny, 3) representing vector fields,
    compute and return an RGB color map based on azimuthal and polar angles.

    Parameters:
    - array: numpy.ndarray with shape (nx, ny, 3), where the last dimension represents the vector components (vx, vy, vz).

    Returns:
    - rgb_colors: numpy.ndarray with shape (nx, ny, 3), representing the RGB colors.
    """
    # Extract vector components
    vx, vy, vz = array[..., 0], array[..., 1], array[..., 2]

    # Compute the magnitude of the vectors
    magnitude_array = np.sqrt(vx**2 + vy**2 + vz**2)

    # Compute the polar angle (θ): angle from the z-axis
    polar_angle_array = np.arccos(vz / magnitude_array)

    # Compute the azimuthal angle (φ): angle in the xy-plane from the x-axis
    azimuthal_angle_array = np.arctan2(vy, vx)

    # Normalize azimuthal angle to [0, 1] for color mapping
    azimuthal_normalized = (azimuthal_angle_array + np.pi) / (2 * np.pi)

    # Map polar angle to brightness (0 for -90°, 1 for 90° in polar coordinates)
    brightness = (polar_angle_array - np.min(polar_angle_array)) / (np.max(polar_angle_array) - np.min(polar_angle_array))

    # Create an HSV color map (Hue from azimuthal, Value from brightness, Saturation=1)
    hsv_colors = np.zeros_like(array)
    hsv_colors[..., 0] = azimuthal_normalized  # Hue
    hsv_colors[..., 1] = 1.0                   # Saturation
    hsv_colors[..., 2] = brightness            # Value

    # Convert HSV to RGB using hsv_to_rgb
    rgb_colors = hsv_to_rgb(hsv_colors)

    return rgb_colors, azimuthal_normalized, brightness, polar_angle_array

def average_vector_field(array, block_size):
    """
    Compute the averaged vector field for an input array by averaging over block_size x block_size blocks.
    If the dimensions are not divisible by block_size, center the averaging window.

    Parameters:
    - array: numpy.ndarray with shape (nx, ny, 3), where the last dimension represents the vector components (vx, vy, vz).
    - block_size: int, the block size for averaging.

    Returns:
    - averaged_array: numpy.ndarray with shape (nx//block_size, ny//block_size, 3) approximately, representing the averaged vector field.
    """
    nx, ny, _ = array.shape

    # Calculate start indices to center the averaging window
    start_x = (nx % block_size) // 2
    start_y = (ny % block_size) // 2

    # Slice the array to ensure divisibility by block_size
    sliced_array = array[start_x:nx - (nx % block_size - start_x), start_y:ny - (ny % block_size - start_y), :]

    # New dimensions after slicing
    new_nx, new_ny, _ = sliced_array.shape

    # Reshape and compute the mean over block_size x block_size blocks
    averaged_array = sliced_array.reshape(new_nx // block_size, block_size, new_ny // block_size, block_size, 3).mean(axis=(1, 3))

    return averaged_array

def compute_azimuthal_and_magnitude(array):
    """
    Compute the azimuthal angle (φ) and the magnitude in the xy-plane for a given vector field.

    Parameters:
    - array: numpy.ndarray with shape (nx, ny, 3), where the last dimension represents the vector components (vx, vy, vz).

    Returns:
    - azimuthal_angle_array: numpy.ndarray with shape (nx, ny), representing the azimuthal angles (φ).
    - magnitude_xy_array: numpy.ndarray with shape (nx, ny), representing the magnitudes in the xy-plane.
    """
    # Extract vector components
    vx, vy, _ = array[..., 0], array[..., 1], array[..., 2]

    # Compute the azimuthal angle (φ): angle in the xy-plane from the x-axis
    azimuthal_angle_array = np.arctan2(vy, vx)

    # Compute the magnitude in the xy-plane
    magnitude_xy_array = np.sqrt(vx**2 + vy**2)

    return azimuthal_angle_array, magnitude_xy_array

def plot_rgb_with_arrows(rgb_colors, azimuthal_angle_array, magnitude_xy_array):
    """
    Plot RGB colormap with arrows overlaid based on azimuthal angles and magnitudes.

    Parameters:
    - rgb_colors: numpy.ndarray with shape (nx, ny, 3), representing the RGB colors.
    - azimuthal_angle_array: numpy.ndarray with shape (nx, ny), azimuthal angles (φ).
    - magnitude_xy_array: numpy.ndarray with shape (nx, ny), magnitudes in the xy-plane.
    """
    nx, ny = azimuthal_angle_array.shape
    x, y = np.meshgrid(np.arange(ny), np.arange(nx))

    # Compute vector components from azimuthal angle and magnitude
    u = magnitude_xy_array * np.cos(azimuthal_angle_array)  # x-component
    v = magnitude_xy_array * np.sin(azimuthal_angle_array)  # y-component

    plt.figure(figsize=(10, 10))

    # Plot the RGB colormap
    plt.imshow(rgb_colors, origin='lower', extent=[0, ny, 0, nx])

    # Overlay the vector field as arrows
    plt.quiver(x, y, u, v, magnitude_xy_array, angles='xy', scale_units='xy', scale=1, color="w", alpha=0.8, pivot='mid')

    plt.colorbar(label='Magnitude')
    plt.title('RGB Colormap with Vector Field')
    plt.xlabel('X-axis')
    plt.ylabel('Y-axis')
    plt.axis('equal')
    plt.show()

# # Create a 128x128 array with a vortex pattern pointing upward
# x, y = np.meshgrid(np.linspace(-1, 1, 128), np.linspace(-1, 1, 128))
# z = np.zeros_like(x)

# # Compute the vortex pattern
# magnitude = np.sqrt(x**2 + y**2) + 1e-5  # Add small value to avoid division by zero
# vx = -y / magnitude  # x-component of the vector
# vy = x / magnitude   # y-component of the vector
# vz = np.ones_like(z) # z-component pointing upward

# # Combine into a single array
# vortex_array = np.stack((vx, vy, vz), axis=-1)

# print(vortex_array.shape)

# l = 5
# new_array = average_vector_field(vortex_array, l)
# print(new_array.shape)

# azimuthal_angle_array, magnitude_xy_array = compute_azimuthal_and_magnitude(new_array)

# print(azimuthal_angle_array.shape, magnitude_xy_array.shape)

# # Convert HSV to RGB using hsv_to_rgb
# rgb_colors, azimuthal_normalized, brightness, polar_angle_array = get_rgb_colormap(vortex_array)

# plot_rgb_with_arrows(rgb_colors, azimuthal_angle_array, magnitude_xy_array)


# # Plot the result
# im = plt.imshow(rgb_colors, origin='lower')
# # plt.imshow(azimuthal_normalized, origin='lower')
# # im = plt.imshow(brightness, origin='lower')
# # im = plt.imshow(polar_angle_array, origin='lower')
# plt.colorbar(im)
# plt.title("Azimuthal and Polar Color Mapping")
# plt.axis('off')
# plt.show()



# example_array = np.array([[[1,2,3],[4,5,6],[7,8,9],[10,11,12]],[[13,14,15],[16,17,18],[19,20,21],[22,23,24]]])
# block_size = 3  # Block size for averaging

# # Apply the average_vector_field function
# averaged_example = average_vector_field(example_array, block_size)

# print(example_array.shape, averaged_example.shape)
# for i in example_array:
#     print(i)
# print(averaged_example)




import numpy as np

# 配列とパラメータ
array = np.arange(100)
block_size = 2

# start_x と有効範囲を計算
nx = len(array)
start_x = (nx % block_size) // 2

sliced_array = array[start_x : nx - (block_size - (start_x + nx % block_size))]

sliced_array = array[start_x : nx - (nx % block_size) // 2]

# 有効なインデックス範囲
valid_indices = np.arange(start_x, nx - (nx % block_size) // 2)

# 平均インデックスを計算
average_indices = [
    np.mean(valid_indices[i * block_size : (i + 1) * block_size])
    for i in range(len(valid_indices) // block_size)
]

print("Average Indices:", average_indices)

start_x = (nx % block_size) // 2
stop_x = nx - (nx % block_size) // 2
print(start_x, stop_x)
print(np.arange(start_x + (block_size-1)/2, stop_x, block_size))
