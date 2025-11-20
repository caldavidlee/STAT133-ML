import kagglehub

# Download latest version
path = kagglehub.dataset_download("axondata/selfie-and-official-id-photo-dataset-18k-images")

print("Path to dataset files:", path)