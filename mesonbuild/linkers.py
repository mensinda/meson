# Copyright 2012-2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import abc
import os
import typing as T

from . import mesonlib

if T.TYPE_CHECKING:
    pass


class StaticLinker:

    def __init__(self, exelist             ):
        self.exelist = exelist

    def can_linker_accept_rsp(self)        :
        """
        Determines whether the linker can accept arguments using the @rsp syntax.
        """
        return mesonlib.is_windows()

    def get_base_link_args(self, options                  )               :
        """Like compilers.get_base_link_args, but for the static linker."""
        return []

    def get_exelist(self)               :
        return self.exelist.copy()

    def get_std_link_args(self)               :
        return []

    def get_buildtype_linker_args(self, buildtype     )               :
        return []

    def get_output_args(self, target     )               :
        return[]

    def get_coverage_link_args(self)               :
        return []

    def build_rpath_args(self, env               , build_dir     , from_dir     ,
                         rpath_paths     , build_rpath     ,
                         install_rpath     )               :
        return []

    def thread_link_flags(self, env               )               :
        return []

    def openmp_flags(self)               :
        return []

    def get_option_link_args(self, options                  )               :
        return []

    @classmethod
    def unix_args_to_native(cls, args             )               :
        return args[:]

    @classmethod
    def native_args_to_unix(cls, args             )               :
        return args[:]

    def get_link_debugfile_args(self, targetfile     )               :
        # Static libraries do not have PDB files
        return []

    def get_always_args(self)               :
        return []

    def get_linker_always_args(self)               :
        return []


class VisualStudioLikeLinker:
    always_args = ['/NOLOGO']

    def __init__(self, machine     ):
        self.machine = machine

    def get_always_args(self)               :
        return self.always_args.copy()

    def get_linker_always_args(self)               :
        return self.always_args.copy()

    def get_output_args(self, target     )               :
        args = []  # type: T.List[str]
        if self.machine:
            args += ['/MACHINE:' + self.machine]
        args += ['/OUT:' + target]
        return args

    @classmethod
    def unix_args_to_native(cls, args             )               :
        from .compilers import VisualStudioCCompiler
        return VisualStudioCCompiler.unix_args_to_native(args)

    @classmethod
    def native_args_to_unix(cls, args             )               :
        from .compilers import VisualStudioCCompiler
        return VisualStudioCCompiler.native_args_to_unix(args)


class VisualStudioLinker(VisualStudioLikeLinker, StaticLinker):

    """Microsoft's lib static linker."""

    def __init__(self, exelist             , machine     ):
        StaticLinker.__init__(self, exelist)
        VisualStudioLikeLinker.__init__(self, machine)


class IntelVisualStudioLinker(VisualStudioLikeLinker, StaticLinker):

    """Intel's xilib static linker."""

    def __init__(self, exelist             , machine     ):
        StaticLinker.__init__(self, exelist)
        VisualStudioLikeLinker.__init__(self, machine)


class ArLinker(StaticLinker):

    def __init__(self, exelist             ):
        super().__init__(exelist)
        self.id = 'ar'
        pc, stdo = mesonlib.Popen_safe(self.exelist + ['-h'])[0:2]
        # Enable deterministic builds if they are available.
        if '[D]' in stdo:
            self.std_args = ['csrD']
        else:
            self.std_args = ['csr']

    def get_std_link_args(self)               :
        return self.std_args

    def get_output_args(self, target     )               :
        return [target]


class ArmarLinker(ArLinker):  # lgtm [py/missing-call-to-init]

    def __init__(self, exelist             ):
        StaticLinker.__init__(self, exelist)
        self.id = 'armar'
        self.std_args = ['-csr']

    def can_linker_accept_rsp(self)        :
        # armar can't accept arguments using the @rsp syntax
        return False


class DLinker(StaticLinker):
    def __init__(self, exelist             , arch     ):
        super().__init__(exelist)
        self.id = exelist[0]
        self.arch = arch

    def get_std_link_args(self)               :
        return ['-lib']

    def get_output_args(self, target     )               :
        return ['-of=' + target]

    def get_linker_always_args(self)               :
        if mesonlib.is_windows():
            if self.arch == 'x86_64':
                return ['-m64']
            elif self.arch == 'x86_mscoff' and self.id == 'dmd':
                return ['-m32mscoff']
            return ['-m32']
        return []


class CcrxLinker(StaticLinker):

    def __init__(self, exelist             ):
        super().__init__(exelist)
        self.id = 'rlink'

    def can_linker_accept_rsp(self)        :
        return False

    def get_output_args(self, target     )               :
        return ['-output=%s' % target]

    def get_linker_always_args(self)               :
        return ['-nologo', '-form=library']


def prepare_rpaths(raw_rpaths     , build_dir     , from_dir     )               :
    # The rpaths we write must be relative if they point to the build dir,
    # because otherwise they have different length depending on the build
    # directory. This breaks reproducible builds.
    internal_format_rpaths = [evaluate_rpath(p, build_dir, from_dir) for p in raw_rpaths]
    ordered_rpaths = order_rpaths(internal_format_rpaths)
    return ordered_rpaths


def order_rpaths(rpath_list             )               :
    # We want rpaths that point inside our build dir to always override
    # those pointing to other places in the file system. This is so built
    # binaries prefer our libraries to the ones that may lie somewhere
    # in the file system, such as /lib/x86_64-linux-gnu.
    #
    # The correct thing to do here would be C++'s std::stable_partition.
    # Python standard library does not have it, so replicate it with
    # sort, which is guaranteed to be stable.
    return sorted(rpath_list, key=os.path.isabs)


def evaluate_rpath(p     , build_dir     , from_dir     )       :
    if p == from_dir:
        return '' # relpath errors out in this case
    elif os.path.isabs(p):
        return p # These can be outside of build dir.
    else:
        return os.path.relpath(os.path.join(build_dir, p), os.path.join(build_dir, from_dir))


class DynamicLinker(metaclass=abc.ABCMeta):

    """Base class for dynamic linkers."""

    _BUILDTYPE_ARGS = {
        'plain': [],
        'debug': [],
        'debugoptimized': [],
        'release': [],
        'minsize': [],
        'custom': [],
    }  # type: T.Dict[str, T.List[str]]

    def _apply_prefix(self, arg     )               :
        if self.prefix_arg is None:
            return [arg]
        elif isinstance(self.prefix_arg, str):
            return [self.prefix_arg + arg]
        return self.prefix_arg + [arg]

    def __init__(self, exelist             , for_machine                        ,
                 id_     , prefix_arg                           ,
                 always_args             , *, version      = 'unknown version'):
        self.exelist = exelist
        self.for_machine = for_machine
        self.version = version
        self.id = id_
        self.prefix_arg = prefix_arg
        self.always_args = always_args

    def __repr__(self)       :
        return '<{}: v{} `{}`>'.format(type(self).__name__, self.version, ' '.join(self.exelist))

    def get_id(self)       :
        return self.id

    def get_version_string(self)       :
        return '({} {})'.format(self.id, self.version)

    def get_exelist(self)               :
        return self.exelist.copy()

    def get_accepts_rsp(self)        :
        # TODO: is it really a matter of is_windows or is it for_windows?
        return mesonlib.is_windows()

    def get_always_args(self)               :
        return self.always_args.copy()

    def get_lib_prefix(self)       :
        return ''

    # XXX: is use_ldflags a compiler or a linker attribute?

    def get_args_from_envvars(self)               :
        flags = os.environ.get('LDFLAGS')
        if not flags:
            return []
        return mesonlib.split_args(flags)

    def get_option_args(self, options                  )               :
        return []

    def has_multi_arguments(self, args             , env               )                       :
        m = 'Language {} does not support has_multi_link_arguments.'
        raise mesonlib.EnvironmentException(m.format(self.id))

    def get_debugfile_args(self, targetfile     )               :
        """Some compilers (MSVC) write debug into a separate file.

        This method takes the target object path and returns a list of
        commands to append to the linker invocation to control where that
        file is written.
        """
        return []

    def get_std_shared_lib_args(self)               :
        return []

    def get_std_shared_module_args(self, options                  )               :
        return self.get_std_shared_lib_args()

    def get_pie_args(self)               :
        # TODO: this really needs to take a boolean and return the args to
        # disable pie, otherwise it only acts to enable pie if pie *isn't* the
        # default.
        m = 'Linker {} does not support position-independent executable'
        raise mesonlib.EnvironmentException(m.format(self.id))

    def get_lto_args(self)               :
        return []

    def sanitizer_args(self, value     )               :
        return []

    def get_buildtype_args(self, buildtype     )               :
        # We can override these in children by just overriding the
        # _BUILDTYPE_ARGS value.
        return self._BUILDTYPE_ARGS[buildtype]

    def get_asneeded_args(self)               :
        return []

    def get_link_whole_for(self, args             )               :
        raise mesonlib.EnvironmentException(
            'Linker {} does not support link_whole'.format(self.id))

    def get_allow_undefined_args(self)               :
        raise mesonlib.EnvironmentException(
            'Linker {} does not support allow undefined'.format(self.id))

    @abc.abstractmethod
    def get_output_args(self, outname     )               :
        pass

    def get_coverage_args(self)               :
        m = "Linker {} doesn't implement coverage data generation.".format(self.id)
        raise mesonlib.EnvironmentException(m)

    @abc.abstractmethod
    def get_search_args(self, dirname     )               :
        pass

    def export_dynamic_args(self, env               )               :
        return []

    def import_library_args(self, implibname     )               :
        """The name of the outputted import library.

        This implementation is used only on Windows by compilers that use GNU ld
        """
        return []

    def thread_flags(self, env               )               :
        return []

    def no_undefined_args(self)               :
        """Arguments to error if there are any undefined symbols at link time.

        This is the inverse of get_allow_undefined_args().

        TODO: A future cleanup might merge this and
              get_allow_undefined_args() into a single method taking a
              boolean
        """
        return []

    def fatal_warnings(self)               :
        """Arguments to make all warnings errors."""
        return []

    def bitcode_args(self)               :
        raise mesonlib.MesonException('This linker does not support bitcode bundles')

    def get_debug_crt_args(self)               :
        return []

    def build_rpath_args(self, env               , build_dir     , from_dir     ,
                         rpath_paths     , build_rpath     ,
                         install_rpath     )               :
        return []

    def get_soname_args(self, env               , prefix     , shlib_name     ,
                        suffix     , soversion     , darwin_versions                   ,
                        is_shared_module      )               :
        return []


class PosixDynamicLinkerMixin:

    """Mixin class for POSIX-ish linkers.

    This is obviously a pretty small subset of the linker interface, but
    enough dynamic linkers that meson supports are POSIX-like but not
    GNU-like that it makes sense to split this out.
    """

    def get_output_args(self, outname     )               :
        return ['-o', outname]

    def get_std_shared_lib_args(self)               :
        return ['-shared']

    def get_search_args(self, dirname     )               :
        return ['-L' + dirname]


class GnuLikeDynamicLinkerMixin:

    """Mixin class for dynamic linkers that provides gnu-like interface.

    This acts as a base for the GNU linkers (bfd and gold), LLVM's lld, and
    other linkers like GNU-ld.
    """

    _BUILDTYPE_ARGS = {
        'plain': [],
        'debug': [],
        'debugoptimized': [],
        'release': ['-O1'],
        'minsize': [],
        'custom': [],
    }  # type: T.Dict[str, T.List[str]]

    def get_buildtype_args(self, buildtype     )               :
        # We can override these in children by just overriding the
        # _BUILDTYPE_ARGS value.
        return mesonlib.listify([self._apply_prefix(a) for a in self._BUILDTYPE_ARGS[buildtype]])

    def get_pie_args(self)               :
        return ['-pie']

    def get_asneeded_args(self)               :
        return self._apply_prefix('--as-needed')

    def get_link_whole_for(self, args             )               :
        if not args:
            return args
        return self._apply_prefix('--whole-archive') + args + self._apply_prefix('--no-whole-archive')

    def get_allow_undefined_args(self)               :
        return self._apply_prefix('--allow-shlib-undefined')

    def get_lto_args(self)               :
        return ['-flto']

    def sanitizer_args(self, value     )               :
        if value == 'none':
            return []
        return ['-fsanitize=' + value]

    def get_coverage_args(self)               :
        return ['--coverage']

    def export_dynamic_args(self, env               )               :
        m = env.machines[self.for_machine]
        if m.is_windows() or m.is_cygwin():
            return self._apply_prefix('--export-all-symbols')
        return self._apply_prefix('-export-dynamic')

    def import_library_args(self, implibname     )               :
        return self._apply_prefix('--out-implib=' + implibname)

    def thread_flags(self, env               )               :
        if env.machines[self.for_machine].is_haiku():
            return []
        return ['-pthread']

    def no_undefined_args(self)               :
        return self._apply_prefix('--no-undefined')

    def fatal_warnings(self)               :
        return self._apply_prefix('--fatal-warnings')

    def get_soname_args(self, env               , prefix     , shlib_name     ,
                        suffix     , soversion     , darwin_versions                   ,
                        is_shared_module      )               :
        m = env.machines[self.for_machine]
        if m.is_windows() or m.is_cygwin():
            # For PE/COFF the soname argument has no effect
            return []
        sostr = '' if soversion is None else '.' + soversion
        return self._apply_prefix('-soname,{}{}.{}{}'.format(prefix, shlib_name, suffix, sostr))

    def build_rpath_args(self, env               , build_dir     , from_dir     ,
                         rpath_paths     , build_rpath     ,
                         install_rpath     )               :
        m = env.machines[self.for_machine]
        if m.is_windows() or m.is_cygwin():
            return []
        if not rpath_paths and not install_rpath and not build_rpath:
            return []
        args = []
        origin_placeholder = '$ORIGIN'
        processed_rpaths = prepare_rpaths(rpath_paths, build_dir, from_dir)
        # Need to deduplicate rpaths, as macOS's install_name_tool
        # is *very* allergic to duplicate -delete_rpath arguments
        # when calling depfixer on installation.
        all_paths = mesonlib.OrderedSet([os.path.join(origin_placeholder, p) for p in processed_rpaths])
        # Build_rpath is used as-is (it is usually absolute).
        if build_rpath != '':
            all_paths.add(build_rpath)

        # TODO: should this actually be "for (dragonfly|open)bsd"?
        if mesonlib.is_dragonflybsd() or mesonlib.is_openbsd():
            # This argument instructs the compiler to record the value of
            # ORIGIN in the .dynamic section of the elf. On Linux this is done
            # by default, but is not on dragonfly/openbsd for some reason. Without this
            # $ORIGIN in the runtime path will be undefined and any binaries
            # linked against local libraries will fail to resolve them.
            args.extend(self._apply_prefix('-z,origin'))

        # In order to avoid relinking for RPATH removal, the binary needs to contain just
        # enough space in the ELF header to hold the final installation RPATH.
        paths = ':'.join(all_paths)
        if len(paths) < len(install_rpath):
            padding = 'X' * (len(install_rpath) - len(paths))
            if not paths:
                paths = padding
            else:
                paths = paths + ':' + padding
        args.extend(self._apply_prefix('-rpath,' + paths))

        # TODO: should this actually be "for solaris/sunos"?
        if mesonlib.is_sunos():
            return args

        # Rpaths to use while linking must be absolute. These are not
        # written to the binary. Needed only with GNU ld:
        # https://sourceware.org/bugzilla/show_bug.cgi?id=16936
        # Not needed on Windows or other platforms that don't use RPATH
        # https://github.com/mesonbuild/meson/issues/1897
        #
        # In addition, this linker option tends to be quite long and some
        # compilers have trouble dealing with it. That's why we will include
        # one option per folder, like this:
        #
        #   -Wl,-rpath-link,/path/to/folder1 -Wl,-rpath,/path/to/folder2 ...
        #
        # ...instead of just one single looooong option, like this:
        #
        #   -Wl,-rpath-link,/path/to/folder1:/path/to/folder2:...
        for p in rpath_paths:
            args.extend(self._apply_prefix('-rpath-link,' + os.path.join(build_dir, p)))

        return args


class AppleDynamicLinker(PosixDynamicLinkerMixin, DynamicLinker):

    """Apple's ld implementation."""

    def get_asneeded_args(self)               :
        return self._apply_prefix('-dead_strip_dylibs')

    def get_allow_undefined_args(self)               :
        return self._apply_prefix('-undefined,dynamic_lookup')

    def get_std_shared_module_args(self, options                  )               :
        return ['-bundle'] + self._apply_prefix('-undefined,dynamic_lookup')

    def get_pie_args(self)               :
        return ['-pie']

    def get_link_whole_for(self, args             )               :
        result = []  # type: T.List[str]
        for a in args:
            result.extend(self._apply_prefix('-force_load'))
            result.append(a)
        return result

    def get_coverage_args(self)               :
        return ['--coverage']

    def sanitizer_args(self, value     )               :
        if value == 'none':
            return []
        return ['-fsanitize=' + value]

    def no_undefined_args(self)               :
        return self._apply_prefix('-undefined,error')

    def get_always_args(self)               :
        return self._apply_prefix('-headerpad_max_install_names') + super().get_always_args()

    def bitcode_args(self)               :
        return self._apply_prefix('-bitcode_bundle')

    def fatal_warnings(self)               :
        return self._apply_prefix('-fatal_warnings')

    def get_soname_args(self, env               , prefix     , shlib_name     ,
                        suffix     , soversion     , darwin_versions                   ,
                        is_shared_module      )               :
        if is_shared_module:
            return []
        install_name = ['@rpath/', prefix, shlib_name]
        if soversion is not None:
            install_name.append('.' + soversion)
        install_name.append('.dylib')
        args = ['-install_name', ''.join(install_name)]
        if darwin_versions:
            args.extend(['-compatibility_version', darwin_versions[0],
                         '-current_version', darwin_versions[1]])
        return args

    def build_rpath_args(self, env               , build_dir     , from_dir     ,
                         rpath_paths     , build_rpath     ,
                         install_rpath     )               :
        if not rpath_paths and not install_rpath and not build_rpath:
            return []
        # Ensure that there is enough space for install_name_tool in-place
        # editing of large RPATHs
        args = self._apply_prefix('-headerpad_max_install_names')
        # @loader_path is the equivalent of $ORIGIN on macOS
        # https://stackoverflow.com/q/26280738
        origin_placeholder = '@loader_path'
        processed_rpaths = prepare_rpaths(rpath_paths, build_dir, from_dir)
        all_paths = mesonlib.OrderedSet([os.path.join(origin_placeholder, p) for p in processed_rpaths])
        if build_rpath != '':
            all_paths.add(build_rpath)
        for rp in all_paths:
            args.extend(self._apply_prefix('-rpath,' + rp))

        return args


class GnuDynamicLinker(GnuLikeDynamicLinkerMixin, PosixDynamicLinkerMixin, DynamicLinker):

    """Representation of GNU ld.bfd and ld.gold."""



class LLVMDynamicLinker(GnuLikeDynamicLinkerMixin, PosixDynamicLinkerMixin, DynamicLinker):

    """Representation of LLVM's lld (not lld-link) linker.

    This is only the posix-like linker.
    """



class CcrxDynamicLinker(DynamicLinker):

    """Linker for Renesis CCrx compiler."""

    def __init__(self, for_machine                        ,
                 *, version      = 'unknown version'):
        super().__init__(['rlink.exe'], for_machine, 'rlink', '',
                         version=version)

    def get_accepts_rsp(self)        :
        return False

    def get_lib_prefix(self)       :
        return '-lib='

    def get_std_shared_lib_args(self)               :
        return []

    def get_output_args(self, outputname     )               :
        return ['-output=%s' % outputname]

    def get_search_args(self, dirname     )                :
        raise EnvironmentError('rlink.exe does not have a search dir argument')

    def get_allow_undefined_args(self)               :
        return []

    def get_soname_args(self, env               , prefix     , shlib_name     ,
                        suffix     , soversion     , darwin_versions                   ,
                        is_shared_module      )               :
        return []


class ArmDynamicLinker(PosixDynamicLinkerMixin, DynamicLinker):

    """Linker for the ARM compiler."""

    def __init__(self, for_machine                        ,
                 *, version      = 'unknown version'):
        super().__init__(['armlink'], for_machine, 'armlink', '', [],
                         version=version)

    def get_accepts_rsp(self)        :
        return False

    def get_std_shared_lib_args(self)                :
        raise mesonlib.MesonException('The Arm Linkers do not support shared libraries')

    def get_allow_undefined_args(self)               :
        return []


class ArmClangDynamicLinker(ArmDynamicLinker):

    """Linker used with ARM's clang fork.

    The interface is similar enough to the old ARM ld that it inherits and
    extends a few things as needed.
    """

    def export_dynamic_args(self, env               )               :
        return ['--export_dynamic']

    def import_library_args(self, implibname     )               :
        return ['--symdefs=' + implibname]


class PGIDynamicLinker(PosixDynamicLinkerMixin, DynamicLinker):

    """PGI linker."""

    def get_allow_undefined_args(self)               :
        return []

    def get_soname_args(self, env               , prefix     , shlib_name     ,
                        suffix     , soversion     , darwin_versions                   ,
                        is_shared_module      )               :
        return []

    def get_std_shared_lib_args(self)               :
        # PGI -shared is Linux only.
        if mesonlib.is_windows():
            return ['-Bdynamic', '-Mmakedll']
        elif mesonlib.is_linux():
            return ['-shared']
        return []

    def build_rpath_args(self, env               , build_dir     , from_dir     ,
                         rpath_paths     , build_rpath     ,
                         install_rpath     )               :
        if not env.machines[self.for_machine].is_windows():
            return ['-R' + os.path.join(build_dir, p) for p in rpath_paths]
        return []


class PGIStaticLinker(StaticLinker):
    def __init__(self, exelist             ):
        super().__init__(exelist)
        self.id = 'ar'
        self.std_args = ['-r']

    def get_std_link_args(self)               :
        return self.std_args

    def get_output_args(self, target     )               :
        return [target]

class VisualStudioLikeLinkerMixin:

    _BUILDTYPE_ARGS = {
        'plain': [],
        'debug': [],
        'debugoptimized': [],
        # The otherwise implicit REF and ICF linker optimisations are disabled by
        # /DEBUG. REF implies ICF.
        'release': ['/OPT:REF'],
        'minsize': ['/INCREMENTAL:NO', '/OPT:REF'],
        'custom': [],
    }  # type: T.Dict[str, T.List[str]]

    def __init__(self, *args, direct       = True, machine      = 'x86', **kwargs):
        super().__init__(*args, **kwargs)
        self.machine = machine

    def invoked_by_compiler(self)        :
        return not self.direct

    def get_debug_crt_args(self)               :
        """Arguments needed to select a debug crt for the linker.

        Sometimes we need to manually select the CRT (C runtime) to use with
        MSVC. One example is when trying to link with static libraries since
        MSVC won't auto-select a CRT for us in that case and will error out
        asking us to select one.
        """
        return self._apply_prefix('/MDd')

    def get_output_args(self, outputname     )               :
        return self._apply_prefix('/MACHINE:' + self.machine) + self._apply_prefix('/OUT:' + outputname)

    def get_always_args(self)               :
        return self._apply_prefix('/nologo') + super().get_always_args()

    def get_search_args(self, dirname     )               :
        return self._apply_prefix('/LIBPATH:' + dirname)

    def get_std_shared_lib_args(self)               :
        return self._apply_prefix('/DLL')

    def get_debugfile_args(self, targetfile     )               :
        pdbarr = targetfile.split('.')[:-1]
        pdbarr += ['pdb']
        return self._apply_prefix('/DEBUG') + self._apply_prefix('/PDB:' + '.'.join(pdbarr))

    def get_link_whole_for(self, args             )               :
        # Only since VS2015
        args = mesonlib.listify(args)
        l = []  # T.List[str]
        for a in args:
            l.extend(self._apply_prefix('/WHOLEARCHIVE:' + a))
        return l

    def get_allow_undefined_args(self)               :
        return []

    def get_soname_args(self, env               , prefix     , shlib_name     ,
                        suffix     , soversion     , darwin_versions                   ,
                        is_shared_module      )               :
        return []


class MSVCDynamicLinker(VisualStudioLikeLinkerMixin, DynamicLinker):

    """Microsoft's Link.exe."""

    def __init__(self, for_machine                        , always_args             , *,
                 exelist                          = None,
                 prefix                            = '',
                 machine      = 'x86', version      = 'unknown version',
                 direct       = True):
        super().__init__(exelist or ['link.exe'], for_machine, 'link',
                         prefix, always_args, machine=machine, version=version, direct=direct)


class ClangClDynamicLinker(VisualStudioLikeLinkerMixin, DynamicLinker):

    """Clang's lld-link.exe."""

    def __init__(self, for_machine                        , always_args             , *,
                 exelist                          = None,
                 prefix                            = '',
                 machine      = 'x86', version      = 'unknown version',
                 direct       = True):
        super().__init__(exelist or ['lld-link.exe'], for_machine, 'lld-link',
                         prefix, always_args, machine=machine, version=version, direct=direct)


class XilinkDynamicLinker(VisualStudioLikeLinkerMixin, DynamicLinker):

    """Intel's Xilink.exe."""

    def __init__(self, for_machine                        , always_args             ,
                 *, version      = 'unknown version'):
        super().__init__(['xilink.exe'], for_machine, 'xilink', '', always_args, version=version)


class SolarisDynamicLinker(PosixDynamicLinkerMixin, DynamicLinker):

    """Sys-V derived linker used on Solaris and OpenSolaris."""

    def get_link_whole_for(self, args             )               :
        if not args:
            return args
        return self._apply_prefix('--whole-archive') + args + self._apply_prefix('--no-whole-archive')

    def no_undefined_args(self)               :
        return ['-z', 'defs']

    def get_allow_undefined_args(self)               :
        return ['-z', 'nodefs']

    def fatal_warnings(self)               :
        return ['-z', 'fatal-warnings']

    def build_rpath_args(self, env               , build_dir     , from_dir     ,
                         rpath_paths     , build_rpath     ,
                         install_rpath     )               :
        if not rpath_paths and not install_rpath and not build_rpath:
            return []
        processed_rpaths = prepare_rpaths(rpath_paths, build_dir, from_dir)
        all_paths = mesonlib.OrderedSet([os.path.join('$ORIGIN', p) for p in processed_rpaths])
        if build_rpath != '':
            all_paths.add(build_rpath)

        # In order to avoid relinking for RPATH removal, the binary needs to contain just
        # enough space in the ELF header to hold the final installation RPATH.
        paths = ':'.join(all_paths)
        if len(paths) < len(install_rpath):
            padding = 'X' * (len(install_rpath) - len(paths))
            if not paths:
                paths = padding
            else:
                paths = paths + ':' + padding
        return self._apply_prefix('-rpath,{}'.format(paths))

    def get_soname_args(self, env               , prefix     , shlib_name     ,
                        suffix     , soversion     , darwin_versions                   ,
                        is_shared_module      )               :
        sostr = '' if soversion is None else '.' + soversion
        return self._apply_prefix('-soname,{}{}.{}{}'.format(prefix, shlib_name, suffix, sostr))


class OptlinkDynamicLinker(VisualStudioLikeLinkerMixin, DynamicLinker):

    """Digital Mars dynamic linker for windows."""

    def __init__(self, for_machine                        ,
                 *, version      = 'unknown version'):
        # Use optlink instead of link so we don't interfer with other link.exe
        # implementations.
        super().__init__(['optlink.exe'], for_machine, 'optlink', '', [], version=version)

    def get_allow_undefined_args(self)               :
        return []

class CudaLinker(PosixDynamicLinkerMixin, DynamicLinker):
    """Cuda linker (nvlink)"""
    @staticmethod
    def parse_version():
        version_cmd = ['nvlink', '--version']
        try:
            _, out, _ = mesonlib.Popen_safe(version_cmd)
        except OSError:
            return 'unknown version'
        # Output example:
        # nvlink: NVIDIA (R) Cuda linker
        # Copyright (c) 2005-2018 NVIDIA Corporation
        # Built on Sun_Sep_30_21:09:22_CDT_2018
        # Cuda compilation tools, release 10.0, V10.0.166
        # we need the most verbose version output. Luckily starting with V
        return out.strip().split('V')[-1]

    def get_accepts_rsp(self)        :
        # nvcc does not support response files
        return False

    def get_lib_prefix(self)       :
        if not mesonlib.is_windows():
            return ''
        # nvcc doesn't recognize Meson's default .a extension for static libraries on
        # Windows and passes it to cl as an object file, resulting in 'warning D9024 :
        # unrecognized source file type 'xxx.a', object file assumed'.
        #
        # nvcc's --library= option doesn't help: it takes the library name without the
        # extension and assumes that the extension on Windows is .lib; prefixing the
        # library with -Xlinker= seems to work.
        from .compilers import CudaCompiler
        return CudaCompiler.LINKER_PREFIX

    def fatal_warnings(self)               :
        return ['--warning-as-error']

    def get_allow_undefined_args(self)               :
        return []

    def get_soname_args(self, env               , prefix     , shlib_name     ,
                        suffix     , soversion     , darwin_versions                   ,
                        is_shared_module      )               :
        return []
