#!/bin/bash

set -e

source /ci/common.sh

pkgs=(
  dev-python/pip dev-python/wheel dev-python/pytest-xdist dev-python/lxml
  dev-python/cython dev-python/jsonschema dev-python/pygobject

  dev-util/cmake dev-util/itstool dev-util/gtk-doc dev-util/vulkan-headers
  dev-util/vulkan-tools
  dev-vcs/git dev-vcs/mercurial

  dev-lang/vala dev-lang/rust-bin dev-lang/mono dev-lang/nasm

  dev-cpp/gtkmm dev-cpp/gtest

  dev-libs/protobuf dev-libs/gobject-introspection
  dev-libs/libxml2 dev-libs/libxslt dev-libs/libyaml dev-libs/glib
  dev-libs/json-glib dev-libs/boost

  dev-qt/qtcore dev-qt/qtgui dev-qt/qtwidgets dev-qt/linguist-tools
  dev-java/openjdk-bin
  # dev-dotnet/gtk-sharp

  sys-devel/gcc sys-devel/clang # This will compile gcc + clang FROM SOURCE which takes ages
  sys-libs/zlib
  sys-cluster/openmpi

  # Skip scientific packages
  # sci-libs/hdf5 sci-libs/netcdf sci-libs/netcdf-cxx
  # sci-libs/scalapack

  x11-libs/wxGTK
  media-libs/libsdl2 media-libs/vulkan-loader media-libs/vulkan-layers media-libs/libwmf
  media-gfx/graphviz

  net-libs/libpcap net-print/cups

  app-doc/doxygen
  app-portage/gentoolkit

  # gnustep-base/gnustep-base
)

echo "Install script $0 started"

# get rid of the warning
eselect news read > /dev/null

# emerge -qv --sync
emerge -qv --update @world

echo "Update complete"
echo ""
echo ""

# Ensure that preinstalled programs exist:
python  --version
ninja   --version
patch   --version
bison   --version
flex    --version
curl    --version
gettext --version

echo ""
echo ""
echo "Setting USE flags"

echo 'USE="X"' >> /etc/portage/make.conf

# echo 'media-libs/mesa -llvm'                               >> /etc/portage/package.use/meson_inst.use
echo 'sys-devel/gcc    d objc objc++'                      >> /etc/portage/package.use/meson_inst.use
echo 'sys-libs/zlib    static-libs'                        >> /etc/portage/package.use/meson_inst.use
echo 'dev-lang/mono    minimal'                            >> /etc/portage/package.use/meson_inst.use
echo 'dev-libs/openssl bindist'                            >> /etc/portage/package.use/meson_inst.use
echo 'dev-libs/boost   python static-libs'                 >> /etc/portage/package.use/meson_inst.use
echo 'dev-qt/qtnetwork bindist'                            >> /etc/portage/package.use/meson_inst.use
echo '>=media-libs/gd-2.3.0 jpeg png truetype fontconfig'  >> /etc/portage/package.use/meson_inst.use
echo '>=dev-libs/libpcre2-10.34 pcre16'                    >> /etc/portage/package.use/meson_inst.use
echo '>=app-text/ghostscript-gpl-9.50 cups'                >> /etc/portage/package.use/meson_inst.use
echo '>=app-text/xmlto-0.0.28-r1 text'                     >> /etc/portage/package.use/meson_inst.use

# Only select intel, other wise mesa would require LLVM which we don't
# want since it takes ages to compile
# export VIDEO_CARDS="intel"

# Work around https://bugs.gentoo.org/617788 by installing dev-libs/boehm-gc manually
# emerge -qv dev-libs/boehm-gc

# List all packages
emerge --pretend "${pkgs[@]}"

# Now compile all packages from source for the next 3h or so
emerge -qv --jobs 2 "${pkgs[@]}"

pip install --user hotdoc
