#!/usr/bin/env python3
"""Build a clean riscv64 tools tree for the in-app Linux guest.

Input: the fixed SHA-pinned files produced by research/linux-job/prepare-inputs.py
(Alpine minirootfs plus the pinned APK set). Output: a root tree suitable for
build-linux-assets.py --tools-root.

No archive scripts run, no network, no test fixtures. The guest agent and
agent-init.sh are added by build-linux-assets.py itself, not here.
"""
import argparse, hashlib, io, json, os, pathlib, shutil, tarfile, zlib

P = pathlib.Path
p = argparse.ArgumentParser()
p.add_argument('--inputs', type=P, required=True, help='prepare-inputs.py output directory')
p.add_argument('--output', type=P, required=True, help='fresh output directory; writes <output>/root')
a = p.parse_args()

HERE = P(__file__).resolve().parent
INPUTS = a.inputs.resolve()
OUT = a.output.resolve()
if OUT.exists():
    p.error('--output must be fresh')
root = OUT / 'root'
root.mkdir(parents=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(t, dest):
    links = []
    for m in t:
        name = pathlib.PurePosixPath(m.name)
        if name.is_absolute() or '..' in name.parts:
            raise ValueError(f'archive path escape: {m.name}')
        path = dest.joinpath(*name.parts)
        if path == dest:
            continue
        cur = dest
        for part in name.parts[:-1]:
            cur = cur / part
            if cur.is_symlink():
                raise ValueError(f'symlink archive parent: {m.name}')
            cur.mkdir(exist_ok=True)
        if m.isdir():
            if path.is_symlink():
                raise ValueError(f'directory replaces symlink: {m.name}')
            path.mkdir(exist_ok=True)
        elif m.isfile():
            if path.exists() or path.is_symlink():
                path.unlink()
            with t.extractfile(m) as source, path.open('xb') as target:
                shutil.copyfileobj(source, target)
        elif m.issym():
            if path.exists() or path.is_symlink():
                path.unlink()
            path.symlink_to(m.linkname)
        elif m.islnk():
            links.append((path, m.linkname))
        else:
            raise ValueError(f'unexpected archive node: {m.name}')
        if not m.issym():
            path.chmod(m.mode & 0o777)
    for path, target in links:
        source = dest / target
        if not source.resolve().is_relative_to(dest) or not source.is_file():
            raise ValueError(f'hard link escape: {target}')
        if path.exists() or path.is_symlink():
            path.unlink()
        os.link(source, path)


ALPINE = 'alpine-minirootfs-3.24.4-riscv64.tar.gz'
ALPINE_SHA = '010683db6c73b3ad1c334fc8f93f64ae748ef67ae6d69e964929aeaf8517bff3'
alpine = INPUTS / ALPINE
if not alpine.is_file() or sha(alpine) != ALPINE_SHA:
    p.error(f'{ALPINE} missing or SHA mismatch')
with tarfile.open(alpine) as t:
    extract(t, root)

lock = json.loads((HERE / 'research/linux-job/packages.lock.json').read_text())
for entry in lock:
    apk = INPUTS / 'apks' / entry['filename']
    if not apk.is_file() or sha(apk) != entry['sha256']:
        p.error(f'APK missing or SHA mismatch: {entry["filename"]}')
    rest = apk.read_bytes()
    members = []
    while rest:
        dec = zlib.decompressobj(31)
        members.append(dec.decompress(rest) + dec.flush())
        rest = dec.unused_data
    if len(members) != 3:
        p.error(f'APK is not a three-member v2 package: {entry["filename"]}')
    with tarfile.open(fileobj=io.BytesIO(members[2])) as t:
        extract(t, root)

(root / 'workspace').mkdir(exist_ok=True)
(root / 'workspace').chmod(0o777)
(root / 'etc' / 'resolv.conf').write_text('nameserver 10.0.2.3\n')

(OUT / 'BUILD.json').write_text(json.dumps({
    'scope': 'Production guest tools tree; no test fixtures, agent or init added here',
    'alpineSha256': ALPINE_SHA,
    'packages': [{'name': e['name'], 'version': e['version'], 'sha256': e['sha256']} for e in lock],
}, indent=2) + '\n')
print(f'tools-root: {root}')
