# computer-vision-project
Fly annotations and other resources

# Google cloud (where all the big files are stored)
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
  
All inputs above are in the `inputs` folder. The files titled _0.ome.tif, _1.ome.tif, _2.ome.tif, etc. are one continuous video split into three parts. Resulting TIF files should go in separate folders, such as the `quiescent_bouts` folder for the output of trackfly.ipynb.

# Accessing the TIFF data

The large TIFF files (~4 GB each) live in a Google Cloud Storage bucket. **Do not download them to your own computer.** Run the code on a VM (section 4), which copies one file at a time from the bucket.

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

The files are OME-TIFF movies (many frames per file). Reading them straight from the bucket is very slow, because every frame needs its own network request. Instead, the notebook copies the file you need to local disk once, then reads it from there. This means it should be run on a VM (section 4), not on your own computer. To use a different file, change `filename` in the notebook's second cell.

```python
import os
import gcsfs
import tifffile

filename = "20250511_1_MMStack_Default_0.ome.tif"   # the only place to change
bucket_path = f"cv-project-storage/{filename}"      # no gs:// prefix
local_path = f"data/{filename}"
fs = gcsfs.GCSFileSystem()

# copy once; skipped if the file is already on this machine
if not os.path.exists(local_path):
    os.makedirs("data", exist_ok=True)
    fs.get(bucket_path, local_path + ".part")
    os.replace(local_path + ".part", local_path)
```

Everything after that reads the local copy:

```python
path = local_path

with tifffile.TiffFile(path) as tif:
    n_frames = len(tif.pages)
    first = tif.pages[0].asarray()                 # one frame

frames = tifffile.imread(path, key=range(0, 2000))    # frames 0-1999 only
```

Load only the frames you need, or loop over them one at a time, rather than loading a whole file into memory.

The notebook saves its results (`features.npz`, `slot_mask.npy` and `clip_500.mp4`) on local disk. To keep them, upload them to the `outputs/` folder in the bucket (never over the original files):

```bash
gcloud storage cp features.npz slot_mask.npy clip_500.mp4 gs://cv-project-storage/outputs/
```

## 4. Running on a VM (for heavy processing)

A VM in the same region as the bucket reads the files fast and with no download fees. You edit in VS Code on your computer, and the code runs on the VM.

### One-time (admin)

Grant the VM's service account read and write access to the bucket.

```bash
gcloud storage buckets add-iam-policy-binding gs://cv-project-storage --member="serviceAccount:96723376457-compute@developer.gserviceaccount.com" --role="roles/storage.objectUser"
```

Contributors also need permission to create and connect to VMs (for example `Compute Instance Admin (v1)` and `Service Account User` on the project).

### Each contributor

1. Create your own VM. Use the same region as the bucket, and your name in the VM name:

   ```bash
   gcloud compute instances create tiff-vm-YOURNAME --zone=us-central1-a --machine-type=e2-standard-8 --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud --boot-disk-size=50GB --scopes=https://www.googleapis.com/auth/devstorage.read_write
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

5. Open the `computer-vision-project` folder in VS Code, open the notebook, choose the `.venv` interpreter when asked (or press `F1` and run **Python: Select Interpreter**), and run all cells.

   The notebook copies the data file onto the VM's disk (about 4 GB per file). The 50 GB disk fits a few files, so delete the local copy when you finish with it:

   ```bash
   rm -r data/
   ```

### Stop the VM when you're done

A running VM costs money. Stopping it keeps your files:

```bash
gcloud compute instances stop tiff-vm-YOURNAME --zone=us-central1-a
gcloud compute instances start tiff-vm-YOURNAME --zone=us-central1-a
```

Delete it when you no longer need it: `gcloud compute instances delete tiff-vm-YOURNAME --zone=us-central1-a`

## 5. Saving your work

Anything only on the VM's disk is lost if the VM is deleted. Save each kind of output in the right place:

| What | Where it goes |
|---|---|
| Code and notebook changes | GitHub |
| Results from trackfly.ipynb (`.csv`, `.npz`, `.npy`, `.mp4`) | The bucket's `quiescent_bouts/` folder |
| Original TIFFs | Already in the bucket, never changed |

### Code changes (GitHub)

Run these in the VM terminal. The first two lines are needed only once per VM:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git add trackfly.ipynb
git commit -m "describe what you changed"
git push
```

If `git push` asks for a password, use VS Code's **Source Control** panel (it can sign in with your GitHub account), or run `sudo apt install gh` and then `gh auth login`.

Run `git status` before committing to check what is about to be added. `data/`, `*.mp4` and `*.npz` must be in `.gitignore`.

### Notebook outputs (plots)

Plots saved inside the `.ipynb` make the file large and cause merge conflicts when two people edit it. To commit only the code, run this once in each clone of the repo (including on each VM):

```bash
pip install nbstripout
nbstripout --install
```

Your notebook still shows its outputs while you work. To keep a plot on purpose, save a small image (for example `plt.savefig("results/movement.png", dpi=150)`) and commit that file. Do not commit videos or data arrays.

### Result files (bucket)

```bash
gcloud storage cp features.npz slot_mask.npy clip_500.mp4 gs://cv-project-storage/outputs/
```

### Before deleting a VM

Make sure `git status` shows nothing uncommitted and that any results you want are uploaded to `outputs/`. The VM's disk is destroyed when the VM is deleted. Stopping a VM keeps its disk.

## Troubleshooting

| Problem | Fix |
|---|---|
| `403 Forbidden` | Your account doesn't have bucket access yet. Ask an admin. |
| `DefaultCredentialsError` | Re-run `gcloud auth application-default login`. |
| `403` on the VM | The VM's service account lacks bucket access, or the VM was created without the read/write storage scope. Ask an admin. |
| `403` when writing from a VM created earlier | Stop the VM, run `gcloud compute instances set-service-account tiff-vm-YOURNAME --zone=us-central1-a --scopes=https://www.googleapis.com/auth/devstorage.read_write`, then start it again. |
| VM not listed in Remote-SSH | Re-run `gcloud compute config-ssh`, and make sure the VM is running. |
| Very slow reads, or the notebook seems stuck | Don't read the file over the network. Copy it to local disk first (section 3). |