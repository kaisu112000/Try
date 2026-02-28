"""
Automation script to run ewfile.py with phone numbers from Lamix CSV.

Usage:
    python run_ewfile.py
    python run_ewfile.py 100
    python run_ewfile.py 100 200
"""

import csv
import subprocess
import sys
import time
import os

# ================= CONFIG =================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(SCRIPT_DIR, "Lamix SMS My SMS Numbers.csv")

BATCH_SIZE = 5
WAIT_BETWEEN_BATCHES = 3  # seconds
TIMEOUT_PER_BATCH = 300   # seconds (5 minutes)
# ===========================================


def load_numbers(csv_path):
    """Read all phone numbers from the CSV 'Number' column."""
    numbers = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            num = row.get("Number", "").strip().strip('"')
            if num:
                numbers.append(num)

    return numbers


def run_batch(batch, batch_num, total_batches):
    """Run ewfile.py with a batch of numbers."""
    print(f"\n{'='*60}")
    print(f"BATCH {batch_num}/{total_batches} -- Numbers: {batch}")
    print(f"{'='*60}\n")

    stdin_text = "\n".join(batch) + "\n\n"

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        script_path = os.path.join(SCRIPT_DIR, "ewfile.py")

        proc = subprocess.Popen(
            [sys.executable, script_path],
            cwd=SCRIPT_DIR,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        stdout, _ = proc.communicate(
            input=stdin_text,
            timeout=TIMEOUT_PER_BATCH
        )

        if stdout:
            for line in stdout.splitlines():
                print(f"  | {line}")

        if proc.returncode != 0:
            print(f"  [!] ewfile.py exited with code {proc.returncode}")

        return proc.returncode if proc.returncode is not None else -1

    except subprocess.TimeoutExpired:
        proc.kill()
        print("  [!] Batch timed out -- killed.")
        return -1

    except Exception as e:
        print(f"  [!] Error running batch: {e}")
        return -1


def main():
    # Check CSV exists
    if not os.path.exists(CSV_FILE):
        print(f"[ERROR] CSV not found: {CSV_FILE}")
        sys.exit(1)

    numbers = load_numbers(CSV_FILE)
    print(f"[INFO] Loaded {len(numbers)} numbers from CSV")

    if not numbers:
        print("[ERROR] No numbers found in CSV!")
        sys.exit(1)

    # Parse optional start/end indexes
    start = 0
    end = len(numbers)

    if len(sys.argv) > 1:
        try:
            start = int(sys.argv[1])
        except ValueError:
            print("Usage: python run_ewfile.py [start_index] [end_index]")
            sys.exit(1)

    if len(sys.argv) > 2:
        try:
            end = int(sys.argv[2])
        except ValueError:
            print("Usage: python run_ewfile.py [start_index] [end_index]")
            sys.exit(1)

    numbers = numbers[start:end]

    total_batches = (len(numbers) + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"[INFO] Processing numbers {start} -> {start + len(numbers) - 1}")
    print(f"[INFO] {len(numbers)} numbers in {total_batches} batches of {BATCH_SIZE}")
    print()

    success = 0
    failed = 0

    for i in range(0, len(numbers), BATCH_SIZE):
        batch = numbers[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1

        rc = run_batch(batch, batch_num, total_batches)

        if rc == 0:
            success += 1
        else:
            failed += 1

        if i + BATCH_SIZE < len(numbers):
            print(f"\n... waiting {WAIT_BETWEEN_BATCHES}s before next batch ...\n")
            time.sleep(WAIT_BETWEEN_BATCHES)

    print("\n" + "=" * 60)
    print(f"DONE -- {success} batches OK, {failed} batches failed")
    print(f"Total numbers processed: {len(numbers)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
