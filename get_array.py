import numpy as np
from matplotlib.colors import hsv_to_rgb

def get_array(self, array, header, variables):
    # Get the currently selected axes
    x_axis = variables["Graph X-Axis"]  # Graph X-Axis
    y_axis = variables["Graph Y-Axis"]  # Graph Y-Axis
    Nx = variables["N" + variables["Graph X-Axis"]]
    Ny = variables["N" + variables["Graph Y-Axis"]]
    plane_index = variables["Plane index"]
    output_format = variables["Output Format"]
    vector_dim = header["valuedim"]

    # Determine the unused axis
    all_axes = ["x", "y", "z"]
    unused_axis = next(axis for axis in all_axes if axis not in [x_axis, y_axis])

    if vector_dim == 1:
        vector_index = 0
    elif "x" == output_format[-1]:
        vector_index = 0
    elif "y" == output_format[-1]:
        vector_index = 1
    elif "z" == output_format[-1]:
        vector_index = 2
    else:
        vector_index = 3

    # Determine the range for the unused axis
    if unused_axis == "x":
        output_array = array[:, :, plane_index, :]
    elif unused_axis == "y":
        output_array = array[:, plane_index, :, :]
    elif unused_axis == "z":
        output_array = array[plane_index, :, :, :]

    self.debug_print("get_array -  vector_index :", vector_index)

    if vector_index != 3:
        output_array = output_array[:, :, vector_index]
        
        self.debug_print("get_array -  output_array.shape :", output_array.shape)
        self.debug_print("get_array -  (Ny, Nx) :", (Ny, Nx))

        if not output_array.shape == (Ny, Nx):
            output_array = np.transpose(output_array)
        
        return output_array, None, None
    else:
        self.debug_print("get_array -  output_array.shape :", output_array.shape)
        self.debug_print("get_array -  (Ny, Nx, 3) :", (Ny, Nx, 3))
        
        if not output_array.shape == (Ny, Nx, 3):
            output_array = np.transpose(output_array, axes=(1, 0, 2))
        
        idx_dict = {"x" : 0, "y" : 1, "z" : 2}
        vector_idx = (idx_dict[x_axis], idx_dict[y_axis], idx_dict[unused_axis])
        self.debug_print("get_array -  vector_idx:", vector_idx)

        self.debug_print("get_array -  self.get_rgb_colormap(output_array).shape :", get_rgb_colormap(output_array, vector_idx).shape)

        arrow_azimuthal_angle_array, arrow_magnitude_xy_array = None, None

        arrow_flag = variables["Show Arrows"]

        if arrow_flag:
            block_size = variables["Block Size"]
            arrow_array = average_vector_field(self, output_array, block_size)
            arrow_azimuthal_angle_array, arrow_magnitude_xy_array = compute_azimuthal_and_magnitude(arrow_array, vector_idx)

        return get_rgb_colormap(output_array, vector_idx), arrow_azimuthal_angle_array, arrow_magnitude_xy_array

def get_rgb_colormap(array, vector_idx):
    """
    Given a 3D array with shape (nx, ny, 3) representing vector fields,
    compute and return an RGB color map based on azimuthal and polar angles.

    Parameters:
    - array: numpy.ndarray with shape (nx, ny, 3), where the last dimension represents the vector components (vx, vy, vz).
    - vector_idx: index of vector

    Returns:
    - rgb_colors: numpy.ndarray with shape (nx, ny, 3), representing the RGB colors.
    """
    # Extract vector components
    vx, vy, vz = array[..., vector_idx[0]], array[..., vector_idx[1]], array[..., vector_idx[2]]

    # Compute the magnitude of the vectors
    magnitude_array = np.sqrt(vx**2 + vy**2 + vz**2)

    # Compute the polar angle (θ): angle from the z-axis
    polar_angle_array = np.arccos(vz / magnitude_array)

    # Compute the azimuthal angle (φ): angle in the xy-plane from the x-axis
    azimuthal_angle_array = np.arctan2(vy, vx)

    # Normalize azimuthal angle to [0, 1] for color mapping
    azimuthal_normalized = (azimuthal_angle_array + np.pi) / (2 * np.pi)

    hue_rotation = 0.5
    # Rotate the hue (azimuthal angle) and ensure it wraps within [0, 1]
    azimuthal_normalized = (azimuthal_normalized + hue_rotation) % 1.0

    # Map polar angle to brightness (1 for 0°, 0 for 180° in polar coordinates)
    brightness = 1 - (polar_angle_array / np.pi)

    max_brightness = np.max(brightness)
    min_brightness = np.min(brightness)

    if max_brightness == min_brightness:
        brightness_normalized = np.ones_like(brightness)  # 最大値と最小値が等しい場合、全て 1
    else:
        brightness_normalized = (brightness - min_brightness) / (max_brightness - min_brightness)  # 0〜1に正規化

    # Create an HSV color map (Hue from azimuthal, Value from brightness, Saturation=1)
    hsv_colors = np.zeros_like(array)
    hsv_colors[..., 0] = azimuthal_normalized  # Hue
    hsv_colors[..., 1] = 1.0                   # Saturation
    hsv_colors[..., 2] = brightness_normalized # Value

    # Convert HSV to RGB using hsv_to_rgb
    rgb_colors = hsv_to_rgb(hsv_colors)

    return rgb_colors

def compute_azimuthal_and_magnitude(array, vector_idx):
    """
    Compute the azimuthal angle (φ) and the magnitude in the xy-plane for a given vector field.

    Parameters:
    - array: numpy.ndarray with shape (nx, ny, 3), where the last dimension represents the vector components (vx, vy, vz).
    - vector_idx: index of vector

    Returns:
    - azimuthal_angle_array: numpy.ndarray with shape (nx, ny), representing the azimuthal angles (φ).
    - magnitude_xy_array: numpy.ndarray with shape (nx, ny), representing the magnitudes in the xy-plane.
    """
    # Extract vector components
    vx, vy, _ = array[..., vector_idx[0]], array[..., vector_idx[1]], array[..., vector_idx[2]]

    # Compute the azimuthal angle (φ): angle in the xy-plane from the x-axis
    azimuthal_angle_array = np.arctan2(vy, vx)

    # Compute the magnitude in the xy-plane
    magnitude_xy_array = np.sqrt(vx**2 + vy**2)

    return azimuthal_angle_array, magnitude_xy_array

def average_vector_field(self, array, block_size):
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
    start_x = (nx % block_size) // 2 if nx > block_size else 0
    start_y = (ny % block_size) // 2 if ny > block_size else 0
    stop_x = nx + start_x - (nx % block_size) if nx > block_size else nx
    stop_y = ny + start_y - (ny % block_size) if ny > block_size else ny

    self.debug_print("average_vector_field -  start_x, stop_x:", start_x, stop_x)
    self.debug_print("average_vector_field -  start_y, stop_y:", start_y, stop_y)
    self.debug_print("average_vector_field -  nx % block_size:", nx % block_size)
    self.debug_print("average_vector_field -  ny % block_size:", ny % block_size)

    # Slice the array to ensure divisibility by block_size
    sliced_array = array[start_x:stop_x, start_y:stop_y, :]

    # New dimensions after slicing
    new_nx, new_ny, _ = sliced_array.shape

    self.debug_print("average_vector_field -  sliced_array.shape:", sliced_array.shape)

    averaged_array_nx = new_nx // block_size if nx > block_size else 1
    averaged_array_ny = new_ny // block_size if ny > block_size else 1
    averaged_array_x_len = block_size if nx > block_size else nx
    averaged_array_y_len = block_size if ny > block_size else ny

    # Reshape and compute the mean over block_size x block_size blocks
    averaged_array = sliced_array.reshape(averaged_array_nx, averaged_array_x_len, averaged_array_ny, averaged_array_y_len, 3).mean(axis=(1, 3))

    self.debug_print("average_vector_field -  averaged_array.shape:", averaged_array.shape)

    return averaged_array