"""Fetch the fixed BPI Challenge 2012 XES file outside the repository."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

DATASET_URL = (
    "https://data.4tu.nl/file/533f66a4-8911-4ac7-8612-1235d65d1f37/"
    "3276db7f-8bee-4f2b-88ee-92dbffb5a893"
)
DATASET_NAME = "BPI_Challenge_2012.xes.gz"
EXPECTED_MD5 = "74c7ba9aba85bfcb181a22c9d565e5b5"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def fetch(data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / DATASET_NAME
    temporary = target.with_suffix(target.suffix + ".part")
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    request = Request(
        DATASET_URL,
        headers={"User-Agent": "process-mining-1c/0.2 (public-study; read-only)"},
    )
    with urlopen(request, timeout=60) as response, temporary.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            md5.update(chunk)
            sha256.update(chunk)
        response_headers = {
            key.lower(): value
            for key, value in response.headers.items()
            if key.lower() in {"content-length", "etag", "last-modified", "content-type"}
        }
    if md5.hexdigest() != EXPECTED_MD5:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("download MD5 does not match the dataset metadata")
    temporary.replace(target)
    write_json(
        data_dir / "fetch-manifest.json",
        {
            "retrieved_at": datetime.now(UTC).isoformat(),
            "dataset": "BPI Challenge 2012",
            "version": 1,
            "doi": "10.4121/uuid:3926db30-f712-4394-aebc-75976070e91f",
            "landing_page": "https://data.4tu.nl/articles/dataset/BPI_Challenge_2012/12689204/1",
            "license": "4TU General Terms of Use",
            "license_url": "https://doi.org/10.4121/resource:terms_of_use",
            "file": DATASET_NAME,
            "download_url": DATASET_URL,
            "metadata_file_id": 24027287,
            "metadata_bytes": 3342406,
            "metadata_md5": EXPECTED_MD5,
            "downloaded_bytes": target.stat().st_size,
            "calculated_md5": md5.hexdigest(),
            "calculated_sha256": sha256.hexdigest(),
            "response_headers": response_headers,
        },
    )
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    print(fetch(args.data_dir))


if __name__ == "__main__":
    main()
