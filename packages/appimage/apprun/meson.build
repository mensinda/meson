project('apprun', ['c'],
  default_options: [
    'warning_level=3',
    'optimization=s',
    'werror=true',
    'debug=false',
    'strip=true',
    'b_lto=true',
    'prefix=/',
  ],
  version: '1.0',
)

fakebin_dir = 'fakebin'
c_flags = [
  '-Wno-pedantic',
  '-DAPPRUN_VERSION="' + meson.project_version() + '"',
  '-DFAKEBIN="' + fakebin_dir + '"',
]
link_flags = ['-static']

common = static_library('common', ['common.c'])

wrappers = {
  'meson': ['-DIS_PYTHON_SCRIPT=1'],
  'ninja': [],
  'cmake': [],
  'pkg-config': [],
  'python3': [],
}

executable('AppRun', ['AppRun.c'],
    link_with:   [common],
    c_args:      c_flags,
    link_args:   link_flags,
    install:     true,
    install_dir: ''
  )

foreach name, extra_flags : wrappers
  base_flags = ['-DREAL_EXE="' + name + '"']

  executable(name, ['wrapper.c'],
    link_with:   [common],
    c_args:      c_flags + base_flags + extra_flags,
    link_args:   link_flags,
    install:     true,
    install_dir: fakebin_dir
  )
endforeach
