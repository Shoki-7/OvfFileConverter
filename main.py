import read_ovf_files as rof
import os
import glob

def main():
    # Directory OVF files
    dir_of_ovf_files = "TestOvfFiles"

    # Get a list of all OVF files in the directory
    ovf_file_path_arr = glob.glob(os.path.join(dir_of_ovf_files, "*.ovf"))

    # Process each OVF file
    for ovf_file_path in ovf_file_path_arr:
        # Read the data and headers from the OVF file
        data, headers = rof.read_ovf_file(ovf_file_path)
        
        # Print headers and data shape
        print("Headers:", headers)
        print("Data shape:", data.shape)
        
        # Access and print a specific data point
        try:
            print("Data at [0, 5, 450]:", data[0, 5, 450])
        except IndexError:
            print("Index out of range for data array in file:", ovf_file_path)

if __name__ == '__main__':
    main()