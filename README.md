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

The files are OME-TIFF movies (many frames per file). Reading them straight from the bucket is very slow, because every frame needs its own network request. Instead, the notebook copies the file you need into a local `temp/` folder once, then reads it from there. This means it should be run on a VM (section 4), not on your own computer. To use a different file, change `filename` in the notebook's second cell. If the file is already in `temp/`, the copy is skipped.

```python
import os
import gcsfs
import tifffile

filename = "20250511_1_MMStack_Default_0.ome.tif"   # the only place to change
temp_dir = "temp"                                      # everything made locally goes here
bucket_path = f"cv-project-storage/inputs/{filename}"  # no gs:// prefix
local_path = f"{temp_dir}/{filename}"
fs = gcsfs.GCSFileSystem()

# copy once; skipped if the file is already on this machine
if not os.path.exists(local_path):
    os.makedirs(temp_dir, exist_ok=True)
    fs.get(bucket_path, local_path + ".part")
    os.replace(local_path + ".part", local_path)
```

Everything after that reads the local copy:

```python
path = local_path

with tifffile.TiffFile(path) as tif:
    n_frames = len(tif.pages)
    first = tif.pages[0].asarray()                 # one frame

frame = tifffile.imread(path, key=100)              # one frame by number
frames = tifffile.imread(path, key=range(0, 500))   # frames 0-499 only
```

Load only the frames you need, or loop over them one at a time, rather than loading a whole file into memory. The notebook processes every frame this way, one at a time.

The pixel sizes used for smoothing and for growing or closing masks were tuned on 688x512 frames. The notebook scales them automatically to each file's frame size.

The copied data file is reused between runs, but every other output is overwritten on each run: each result replaces the file with the same name in the bucket.

### Quiescent bouts

The notebook saves the quiescent bouts as a small CSV instead of copying the frames out. Its cell after the movement check writes `<file>_quiescent_bouts.csv` (one row per bout: `file`, `bout`, `start_frame`, `end_frame`, `n_frames`) and uploads it to the `quiescent_bouts/` folder in the bucket, together with the check plot as `<file>_check_plot.svg`. Frame numbers count within that input file, and `end_frame` is not included.

To get a bout's frames later, download the CSV and read just those frames from the original file (`path` is the local copy of the file named in the CSV's `file` column, set up as above):

```bash
gcloud storage cp gs://cv-project-storage/quiescent_bouts/20250511_1_MMStack_Default_0_quiescent_bouts.csv .
```

```python
import csv
import tifffile

with open("20250511_1_MMStack_Default_0_quiescent_bouts.csv") as fh:
    bouts = list(csv.DictReader(fh))

b = bouts[3]                                                # bout number 3
frames = tifffile.imread(path, key=range(int(b["start_frame"]), int(b["end_frame"])))
```

### Slot mask and features

The notebook also uploads the slot mask and the per-frame features to the `outputs/` folder in the bucket as `<file>_slot_mask.npy` and `<file>_features.npz`, so each input file gets its own pair. `features.npz` holds the per-frame measurements, so you can rerun the movement cell without repeating the slow loop over every frame. To load it later:

```python
import numpy as np

fs.get("cv-project-storage/outputs/20250511_1_MMStack_Default_0_features.npz", f"{temp_dir}/features.npz")
d = np.load(f"{temp_dir}/features.npz")
feats, iou = d["feats"], d["iou"]
```

### Video clip

The video clip (`clip_500.mp4`) is a visual check. Its cell is commented out in the notebook by default, and the file stays in `temp/` on the VM. To keep it, upload it to the `outputs/` folder in the bucket (never over the original files):

```bash
gcloud storage cp temp/clip_500.mp4 gs://cv-project-storage/outputs/
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

   The notebook copies the data file into the VM's `temp/` folder (about 4 GB per file). The 50 GB disk fits a few files, so delete the temp folder when you finish with it:

   ```bash
   rm -r temp/
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
| Quiescent bouts (`.csv`) and the check plot (`.svg`) from trackfly.ipynb | The bucket's `quiescent_bouts/` folder (uploaded by the notebook) |
| Slot mask and features (`.npy`, `.npz`) from trackfly.ipynb | The bucket's `outputs/` folder (uploaded by the notebook) |
| Video clips (`.mp4`) | The bucket's `outputs/` folder (upload by hand) |
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

Run `git status` before committing to check what is about to be added. `temp/`, `*.mp4` and `*.npz` must be in `.gitignore`.

### Notebook outputs (plots)

Plots saved inside the `.ipynb` make the file large and cause merge conflicts when two people edit it. To commit only the code, run this once in each clone of the repo (including on each VM):

```bash
pip install nbstripout
nbstripout --install
```

Your notebook still shows its outputs while you work. To keep a plot on purpose, save a small image (for example `plt.savefig("results/movement.png", dpi=150)`) and commit that file. Do not commit videos or data arrays.

### Video clips (bucket)

```bash
gcloud storage cp temp/clip_500.mp4 gs://cv-project-storage/outputs/
```

### Before deleting a VM

Make sure `git status` shows nothing uncommitted and that any results you want are in the bucket (`quiescent_bouts/` and `outputs/`). The notebook uploads the CSV, plot, slot mask and features itself, but video clips need to be uploaded by hand. The VM's disk is destroyed when the VM is deleted. Stopping a VM keeps its disk.

## Troubleshooting

| Problem | Fix |
|---|---|
| `403 Forbidden` | Your account doesn't have bucket access yet. Ask an admin. |
| `DefaultCredentialsError` | Re-run `gcloud auth application-default login`. |
| `403` on the VM | The VM's service account lacks bucket access, or the VM was created without the read/write storage scope. Ask an admin. |
| `403` when writing from a VM created earlier | Stop the VM, run `gcloud compute instances set-service-account tiff-vm-YOURNAME --zone=us-central1-a --scopes=https://www.googleapis.com/auth/devstorage.read_write`, then start it again. |
| VM not listed in Remote-SSH | Re-run `gcloud compute config-ssh`, and make sure the VM is running. |
| Very slow reads, or the notebook seems stuck | Don't read the file over the network. Copy it to local disk first (section 3). |