#!/usr/bin/env python3
"""Upload PDF(s) to mcp.request.pt and print file_id(s).

Usage:
    python3 upload.py <file.pdf>              # single file
    python3 upload.py <file1.pdf> <file2.pdf>  # multiple files
    python3 upload.py <directory>               # all PDFs in dir
"""

import glob
import json
import mimetypes
import os
import sys
import urllib.request

SETTINGS = os.path.expanduser("~/.claude/settings.json")
UPLOAD_URL = "https://mcp.request.pt/upload"
BOUNDARY = "----PythonFormBoundary"


def get_token():
    with open(SETTINGS) as f:
        return json.load(f)["env"]["REQUEST_MCP_TOKEN"]


def upload(pdf_path, token):
    filename = os.path.basename(pdf_path)
    content_type = mimetypes.guess_type(pdf_path)[0] or "application/pdf"

    with open(pdf_path, "rb") as f:
        data = f.read()

    body = (
        f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + data + f"\r\n--{BOUNDARY}--\r\n".encode()

    req = urllib.request.Request(UPLOAD_URL, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={BOUNDARY}")

    resp = json.loads(urllib.request.urlopen(req).read())
    return resp


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 upload.py <file.pdf|directory> [...]", file=sys.stderr)
        sys.exit(1)

    token = get_token()
    paths = []

    for arg in sys.argv[1:]:
        if os.path.isdir(arg):
            paths.extend(sorted(glob.glob(os.path.join(arg, "*.pdf"))))
        elif os.path.isfile(arg):
            paths.append(arg)
        else:
            print(f"SKIP: {arg} (not found)", file=sys.stderr)

    if not paths:
        print("No PDF files found.", file=sys.stderr)
        sys.exit(1)

    for pdf_path in paths:
        try:
            resp = upload(pdf_path, token)
            file_id = resp.get("file_id", "")
            if file_id:
                print(f"{os.path.basename(pdf_path)}\t{file_id}")
            else:
                print(f"{os.path.basename(pdf_path)}\tERROR: {resp}", file=sys.stderr)
        except Exception as e:
            print(f"{os.path.basename(pdf_path)}\tERROR: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
