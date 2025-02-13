#!/bin/bash

# Define the folder path (change as needed)
FOLDER_PATH="~/actions-runner/hardware_in-loop-testing/tests"  # Change this to your target folder

# Make sure the folder exists
if [ ! -d "$FOLDER_PATH" ]; then
    echo "Error: Directory $FOLDER_PATH does not exist."
    exit 1
fi

# Iterate through all files in the folder
for file in "$FOLDER_PATH"/*; do
    if [ -f "$file" ]; then
        # Check if the file is not executable
        if [ ! -x "$file" ]; then
            echo "Making executable: $file"
            chmod +x "$file"
        fi
        
        # Execute the file
        echo "Executing: $file"
        "$file"
    fi
done
