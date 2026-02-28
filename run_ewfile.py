"""
Automation script to run ewfile.py with phone numbers from Lamix CSV.

Features:
- Skips already processed numbers (processed.txt)
- Runs 5 batches in parallel
- Saves successful numbers automatically
- Resume supported
"""

import csv
import subprocess
import sys
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= CONFIG =================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(SCRIPT_DIR, "Lamix SMS  My SMS Numbers.csv")
PROCESSED_FILE = os.path.join(SCRIPT_DIR, "processed.txt")

BATCH_SIZE = 5
MAX_PARALLEL = 5
TIMEOUT_PER_BATCH = 300
WAIT_BETWEEN_BATCHES = 1
# ==========================================


# ---------- Load Numbers from CSV ----------
def load_numbers(csv_path):
    numbers = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            num = row["Number"].strip().strip('"')
            if num:
                numbers.append(num)
    return numbers


# ---------- Load Processed Numbers ----------
def load_processed():
    if not os.path.exists(PROCESSED_FILE):
        return set()

    with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


# ---------- Save Processed ----------
def save_processed(batch):
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        for num in batch:
            f.write(num + "\n")


# ---------- Run Batch ----------
def run_batch(batch, batch_num, total_batches):
    print(f"\n{'='*60}")
    print(f"  >>> BATCH {batch_num}/{total_batches}")
    print(f"  >>> Numbers: {batch}")
    print(f"{'='*60}")

    stdin_text = "\n".join(batch) + "\n\n\n"

    try:
        proc = subprocess.Popen(
            ["python", "ewfile.py"],   # Termux safe
            cwd=SCRIPT_DIR,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        stdout, _ = proc.communicate(input=stdin_text, timeout=TIMEOUT_PER_BATCH)

        if stdout:
            for line in stdout.splitlines():
                print(f"  | {line}")

        if proc.returncode != 0:
            print(f"  [!] Batch exited with code {proc.returncode}")
            return -1

        print("  ✔ Batch Completed Successfully")
        return 0

    except subprocess.TimeoutExpired:
        proc.kill()
        print("  [!] Batch Timed Out")
        return -1

    except Exception as e:
        print(f"  [!] Error: {e}")
        return -1


# ---------- MAIN ----------
def main():

    if not os.path.exists(CSV_FILE):
        print(f"[ERROR] CSV not found: {CSV_FILE}")
        sys.exit(1)

    numbers = load_numbers(CSV_FILE)
    print(f"[INFO] Loaded {len(numbers)} numbers from CSV")

    if not numbers:
        print("[ERROR] No numbers found!")
        sys.exit(1)

    # Load processed
    processed_numbers = load_processed()
    original_count = len(numbers)

    numbers = [n for n in numbers if n not in processed_numbers]

    skipped = original_count - len(numbers)

    print(f"[INFO] Skipped {skipped} already processed numbers")
    print(f"[INFO] Remaining to process: {len(numbers)}")

    if not numbers:
        print("[INFO] Nothing left to process.")
        return

    # Create batches
    batches = [
        numbers[i:i + BATCH_SIZE]
        for i in range(0, len(numbers), BATCH_SIZE)
    ]

    total_batches = len(batches)

    success = 0
    failed = 0

    print(f"[INFO] Running {total_batches} batches (5 parallel workers)\n")

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        futures = {
            executor.submit(run_batch, batch, idx + 1, total_batches): batch
            for idx, batch in enumerate(batches)
        }

        for future in as_completed(futures):
            batch = futures[future]
            rc = future.result()

            if rc == 0:
                success += 1
                save_processed(batch)
            else:
                failed += 1

            print(f"\n>>> Progress: {success + failed}/{total_batches} batches done")

            time.sleep(WAIT_BETWEEN_BATCHES)

    print(f"\n{'='*60}")
    print(f"  DONE")
    print(f"  Successful Batches: {success}")
    print(f"  Failed Batches: {failed}")
    print(f"  Total Numbers Processed This Run: {len(numbers)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()