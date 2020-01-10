#!/usr/bin/env python3

# Copyright 2020 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .modules import (
    FixUnusedImports,
    TypeHintsRemover,
    ConvertFStrings,
    CodeFormater,
    PostProcessBase,
)

from pathlib import Path
import argparse
import os
import shutil

SKIP_DIRS = [
    '__pycache__',
    '.mypy_cache', '.pytest_cache',
    '.git',
    '.dub', 'meson.egg-info',
    'meson/build', 'meson/dist',
    'meson-logs', 'meson-private',
    '.eggs',
    '.vscode', '.idea', '.cproject', '.pydevproject', '.project',
    'work area',
    'install dir'
]

def main()       :
    parser = argparse.ArgumentParser('Meson code post-processor')
    parser.add_argument('--hints', '-H', action='store_true', help='Removes type hints')
    parser.add_argument('--imports', '-i', action='store_true', help='Remove unused imports')
    parser.add_argument('--fstrings', '-F', action='store_true', help='Convert f-strings to .format()')
    parser.add_argument('--format', '-f', action='store_true', help='Format the result')
    parser.add_argument('--all', '-a', action='store_true', help='Execute all actions')
    parser.add_argument('--verbose', '-V', action='count', default=0, help='Set verbose output level')
    parser.add_argument('out', metavar='DIR', type=str, help='Output directory for the converted files')
    args = parser.parse_args()

    actions                          = []
    sources                              = []
    ncopied = 0
    missing_imports                            = []

    def add_action(a                 )        :
        nonlocal actions, missing_imports
        if not a.check():
            print('ERROR: Failed to load the {} postprocessor'.format(a.name))
            missing_imports += a.imports
        actions += [a]

    # Add post processors
    if args.hints or args.all:
        add_action(TypeHintsRemover())

    if args.fstrings or args.all:
        add_action(ConvertFStrings())

    if args.imports or args.all:
        add_action(FixUnusedImports())

    if args.format or args.all:
        add_action(CodeFormater())

    if missing_imports:
        print('')
        print('Failed to import the following modules:')
        for i in missing_imports:
            print('  - {:<12} url: {}'.format(i[0], i[1]))
        print('')
        print('Try: pip install {}'.format(" ".join([x[0] for x in missing_imports])))
        return 2

    meson_root = Path(__file__).parent.parent.parent.absolute()
    outdir = Path(args.out).absolute()
    if outdir.exists():
        print('ERROR: {} already exists.'.format(outdir))
        return 1

    print('Output will be written to {}'.format(outdir))
    print('Scanning files in {} ...'.format(meson_root))

    # Start by scanning the meson root
    for root, _, files in os.walk(meson_root):
        r_posix = Path(root).as_posix()
        if any({r_posix.endswith('/{}'.format(x)) or '/{}/'.format(x) in r_posix for x in SKIP_DIRS}):
            continue

        for f in files:
            src = Path(root, f)
            dst = Path(outdir, Path(root).relative_to(meson_root), f)

            # Always make sure the directory structure exists
            if not dst.parent.exists():
                dst.parent.mkdir(parents=True)

            if f.endswith('.py'):
                # Remember python files to convert
                sources += [(src, dst)]
            else:
                # Copy none python files
                if args.verbose >= 2:
                    print('  -- Copying {}'.format(src.relative_to(meson_root)))

                shutil.copy2(src, dst)
                ncopied += 1

    # Process python files
    print('Processing python files...')

    try:
        from tqdm import tqdm  # type: ignore
        src_iter                                  = tqdm(sources, unit='files', leave=False)
    except ImportError:
        print('WARNING: Failed to import tqdm! ==> No progress bar.')
        src_iter = sources

    for src, dst in src_iter:
        raw = src.read_text()

        if args.verbose >= 1:
            print('  -- Processing {}'.format(src.relative_to(meson_root)))

        # Skip empty files
        if not raw:
            dst.touch(mode=src.stat().st_mode)
            continue

        for a in actions:
            new_str = a.apply(raw)
            if not new_str:
                print('ERROR: applying {} returned an empty string for {}'.format(a.name, src.relative_to(meson_root)))
                continue
            raw = new_str

        dst.write_text(raw)
        dst.chmod(src.stat().st_mode)

    print('Done. Statistics:')
    print('  -- files processed: {}'.format(len(sources)))
    print('  -- files copied:    {}'.format(ncopied))
    print('  -- actions applied: {}'.format(len(actions)))
    return 0
