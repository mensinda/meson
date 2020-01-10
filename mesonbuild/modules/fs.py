# Copyright 2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import typing as T
import hashlib
from pathlib import Path, PurePath

from .. import mlog
from . import ExtensionModule
from . import ModuleReturnValue
from ..mesonlib import MesonException

from ..interpreterbase import stringArgs, noKwargs
if T.TYPE_CHECKING:
    pass

class FSModule(ExtensionModule):

    def __init__(self, interpreter):
        super().__init__(interpreter)
        self.snippets.add('generate_dub_file')

    def _resolve_dir(self, state               , arg     )        :
        """
        resolves (makes absolute) a directory relative to calling meson.build,
        if not already absolute
        """
        return Path(state.source_root) / state.subdir / Path(arg).expanduser()

    def _check(self, check     , state               , args                 )                     :
        if len(args) != 1:
            raise MesonException('fs.{} takes exactly one argument.'.format(check))
        test_file = self._resolve_dir(state, args[0])
        return ModuleReturnValue(getattr(test_file, check)(), [])

    @stringArgs
    @noKwargs
    def exists(self, state               , args                 , kwargs      )                     :
        return self._check('exists', state, args)

    @stringArgs
    @noKwargs
    def is_symlink(self, state               , args                 , kwargs      )                     :
        return self._check('is_symlink', state, args)

    @stringArgs
    @noKwargs
    def is_file(self, state               , args                 , kwargs      )                     :
        return self._check('is_file', state, args)

    @stringArgs
    @noKwargs
    def is_dir(self, state               , args                 , kwargs      )                     :
        return self._check('is_dir', state, args)

    @stringArgs
    @noKwargs
    def hash(self, state               , args                 , kwargs      )                     :
        if len(args) != 2:
            raise MesonException('method takes exactly two arguments.')
        file = self._resolve_dir(state, args[0])
        if not file.is_file():
            raise MesonException('{} is not a file and therefore cannot be hashed'.format(file))
        try:
            h = hashlib.new(args[1])
        except ValueError:
            raise MesonException('hash algorithm {} is not available'.format(args[1]))
        mlog.debug('computing {} sum of {} size {} bytes'.format(args[1], file, file.stat().st_size))
        h.update(file.read_bytes())
        return ModuleReturnValue(h.hexdigest(), [])

    @stringArgs
    @noKwargs
    def size(self, state               , args                 , kwargs      )                     :
        if len(args) != 1:
            raise MesonException('method takes exactly one argument.')
        file = self._resolve_dir(state, args[0])
        if not file.is_file():
            raise MesonException('{} is not a file and therefore cannot be sized'.format(file))
        try:
            return ModuleReturnValue(file.stat().st_size, [])
        except ValueError:
            raise MesonException('{} size could not be determined'.format(args[0]))

    @stringArgs
    @noKwargs
    def is_samepath(self, state               , args                 , kwargs      )                     :
        if len(args) != 2:
            raise MesonException('fs.is_samepath takes exactly two arguments.')
        file1 = self._resolve_dir(state, args[0])
        file2 = self._resolve_dir(state, args[1])
        if not file1.exists():
            return ModuleReturnValue(False, [])
        if not file2.exists():
            return ModuleReturnValue(False, [])
        try:
            return ModuleReturnValue(file1.samefile(file2), [])
        except OSError:
            return ModuleReturnValue(False, [])

    @stringArgs
    @noKwargs
    def replace_suffix(self, state               , args                 , kwargs      )                     :
        if len(args) != 2:
            raise MesonException('method takes exactly two arguments.')
        original = PurePath(args[0])
        new = original.with_suffix(args[1])
        return ModuleReturnValue(str(new), [])

    @stringArgs
    @noKwargs
    def parent(self, state               , args                 , kwargs      )                     :
        if len(args) != 1:
            raise MesonException('method takes exactly one argument.')
        original = PurePath(args[0])
        new = original.parent
        return ModuleReturnValue(str(new), [])

    @stringArgs
    @noKwargs
    def name(self, state               , args                 , kwargs      )                     :
        if len(args) != 1:
            raise MesonException('method takes exactly one argument.')
        original = PurePath(args[0])
        new = original.name
        return ModuleReturnValue(str(new), [])

def initialize(*args, **kwargs)            :
    return FSModule(*args, **kwargs)
