# computer-vision-project
Fly annotations and other resources

# google cloud (where all the big files are stored)
https://console.cloud.google.com/storage/browser?organizationId=0&project=cv-project-storage&prefix=&forceOnBucketsSortingFiltering=true&bucketType=live

### R22H05_Gal4_UAS_RSET_G8s_het
20250311_Fly1_1_MMStack_Default.ome.tif  
20250311_Fly1_2_MMStack_Default.ome.tif  
20250311_Fly1_3_MMStack_Default.ome.tif  
20250311_Fly1_4_MMStack_Default.ome.tif  
20250311_Fly1_5_MMStack_Default.ome.tif  
20250311_Fly1_6_MMStack_Default.ome.tif  
20250311_Fly2_1_MMStack_Default.ome.tif  
20250311_Fly2_2_MMStack_Default.ome.tif  
20250311_Fly2_3_MMStack_Default.ome.tif  

### R22H05_Gal4_Bl_49_002_UAS_RSET_GCamp8s
20250511_1_MMStack_Default_0.ome.tif  
20250511_1_MMStack_Default_1.ome.tif  
20250511_1_MMStack_Default_2.ome.tif  
20250511_2_MMStack_Default_0.ome.tif  
20250511_2_MMStack_Default_1.ome.tif  
20250511_2_MMStack_Default_2.ome.tif  
20250711_Fly1_1_MMStack_Default.ome.tif  
20250711_Fly1_2_MMStack_Default.ome.tif  
20250711_Fly2_1_MMStack_Default.ome.tif  
20250711_Fly2_2_MMStack_Default.ome.tif  
  
The files titled _0.ome.tif, _1.ome.tif, _2.ome.tif, etc. are one continuous video split into three parts.

# Accessing the TIFF data

The large TIFF files (~4 GB each) live in a Google Cloud Storage bucket. **Do not download them.** The code reads them directly from the bucket.

## 1. Get access

Ask a project admin to grant your Google account the **Storage Object User** role on the bucket:

- Bucket: `gs://cv-project-storage`
- Path: `gs://cv-project-storage/[path]/`

## 2. One-time setup

1. Install [Python 3.10+](https://www.python.org/downloads/) and the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install).
2. Clone the repo and install dependencies:

   ```bash
   git clone https://github.com/mywwyx26/computer-vision-project.git
   cd computer-vision-project
   pip install -r requirements.txt
   ```

3. Log in (opens a browser; use the Google account that was granted access):

   ```bash
   gcloud auth application-default login
   gcloud config set project cv-project-storage
   ```

4. Check it works:

   ```bash
   gcloud storage ls gs://cv-project-storage/[path]/
   ```

## 3. Reading and writing files in code

```python
import rasterio
from rasterio.windows import Window

with rasterio.open("gs://cv-project-storage/[path]/[image.tif]") as src: # replace with actual tif path
    tile = src.read(1, window=Window(0, 0, 1024, 1024))  # reads only this region
```

Read windows or tiles rather than whole files whenever possible.

To save results, write to a separate folder in the bucket (never over the original files):

```python
# directly from code
with rasterio.open("gs://cv-project-storage/outputs/result.tif", "w", **profile) as dst:
    dst.write(data)
```

```bash
# or upload an existing file
gcloud storage cp result.tif gs://cv-project-storage/outputs/
```

## 4. Running on a VM (for heavy processing)

A VM in the same region as the bucket reads the files fast and with no download fees. You edit in VS Code on your computer, and the code runs on the VM.

### One-time (admin)

Grant the VM's service account read and write access to the bucket.

```bash
gcloud storage buckets add-iam-policy-binding gs://cv-project-storage \
  --member="serviceAccount:96723376457-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectUser"
```

Contributors also need permission to create and connect to VMs (for example `Compute Instance Admin (v1)` and `Service Account User` on the project).

### Each contributor

1. Create your own VM. Use the same region as the bucket, and your name in the VM name:

   ```bash
   gcloud compute instances create tiff-vm-YOURNAME \
    --zone=us-central1-a \
    --machine-type=e2-standard-8 \
    --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
    --boot-disk-size=50GB \
    --scopes=https://www.googleapis.com/auth/devstorage.read_write
   ```

   If your code runs out of memory (MemoryError, or the process is "Killed"), resize the VM. Stop it first, since the machine type can't be changed while it is running:

    ```bash
    gcloud compute instances stop tiff-vm-YOURNAME --zone=us-central1-a
    gcloud compute instances set-machine-type tiff-vm-YOURNAME --zone=us-central1-a --machine-type=e2-highmem-16
    gcloud compute instances start tiff-vm-YOURNAME --zone=us-central1-a
    ```

2. Set up SSH (Windows 10/11 already includes the OpenSSH client):

   ```bash
   gcloud compute config-ssh
   ```

3. In VS Code, install the **Remote - SSH** extension. Press `F1`, choose **Remote-SSH: Connect to Host**, and select `tiff-vm-YOURNAME.us-central1-a.cv-project-storage`. Install the **Python** extension on the remote side when prompted.

4. In the VS Code terminal (now on the VM), set up the repo:

   ```bash
   sudo apt update && sudo apt install -y python3-venv git
   git clone https://github.com/mywwyx26/computer-vision-project.git
   cd computer-vision-project
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

   No login is needed on the VM. It authenticates to the bucket automatically.

5. Open the `computer-vision-project` folder in VS Code and run your code as normal.

### Stop the VM when you're done

A running VM costs money. Stopping it keeps your files:

```bash
gcloud compute instances stop tiff-vm-YOURNAME --zone=us-central1-a
gcloud compute instances start tiff-vm-YOURNAME --zone=us-central1-a   # to resume
```

Delete it when you no longer need it: `gcloud compute instances delete tiff-vm-YOURNAME --zone=us-central1-a`

## Troubleshooting

| Problem | Fix |
|---|---|
| `403 Forbidden` | Your account doesn't have bucket access yet. Ask an admin. |
| `DefaultCredentialsError` | Re-run `gcloud auth application-default login`. |
| `403` on the VM | The VM's service account lacks bucket access, or the VM was created without the read/write storage scope. Ask an admin. |
| `403` when writing from a VM created earlier | Stop the VM, run `gcloud compute instances set-service-account tiff-vm-YOURNAME --zone=us-central1-a --scopes=https://www.googleapis.com/auth/devstorage.read_write`, then start it again. |
| VM not listed in Remote-SSH | Re-run `gcloud compute config-ssh`, and make sure the VM is running. |
| Very slow reads | The file may not be a Cloud Optimized GeoTIFF. Ask an admin before converting. |
