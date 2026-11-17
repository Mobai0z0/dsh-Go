#!/usr/bin/env python3
"""Writes the version a HAP reports into AppScope/app.json5.

    hap-version.py --pubspec app/pubspec.yaml --app-json app/ohos/AppScope/app.json5 [--name 1.1.0]

versionName is `--name`, else pubspec's `version:` without the `+N` placeholder.
versionCode is derived, never pubspec's build number: that placeholder stays at 1,
and a phone only installs a HAP whose versionCode is higher than the installed
one, so a fixed number means every release after the first looks like a downgrade.
major*1000000 + minor*10000 + patch*100 keeps the existing 1000000 for 1.0.0 and
still sorts 1.0.16 below 1.1.0.
"""
import argparse
import re
import sys
from pathlib import Path


def version_code(name):
    m = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(-[0-9A-Za-z.-]+)?', name)
    if not m:
        raise ValueError(f'{name!r} is not major.minor.patch')
    major, minor, patch = (int(part) for part in m.groups()[:3])
    if minor > 99 or patch > 99:
        raise ValueError(f'{name} does not fit major*1000000 + minor*10000 + patch*100')
    # A pre-release of a version installs before the release of the same name:
    # one below it, still above the previous patch.
    code = major * 1000000 + minor * 10000 + patch * 100 - (1 if m.group(4) else 0)
    if not 0 < code < 2 ** 31:
        raise ValueError(f'{name} is out of the versionCode range')
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--pubspec', type=Path, required=True)
    parser.add_argument('--app-json', type=Path, required=True)
    parser.add_argument('--name', default='', help='versionName to write; default pubspec version')
    args = parser.parse_args()
    try:
        name = args.name.strip() or re.search(r'^version: *([^+\s]+)',
                                              args.pubspec.read_text(encoding='utf-8'), re.M).group(1)
        code = version_code(name)
    except (ValueError, AttributeError, OSError) as error:
        sys.exit(f'hap-version: {error}')
    text = args.app_json.read_text(encoding='utf-8')
    text, codes = re.subn(r'"versionCode": *\d+', f'"versionCode": {code}', text)
    text, names = re.subn(r'"versionName": *"[^"]*"', f'"versionName": "{name}"', text)
    if codes != 1 or names != 1:
        sys.exit('hap-version: app.json5 no longer has one versionCode and one versionName')
    args.app_json.write_text(text, encoding='utf-8')
    print(f'hap-version: {name} ({code})')


if __name__ == '__main__':
    main()
