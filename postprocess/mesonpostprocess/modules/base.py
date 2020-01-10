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


class PostProcessBase:
    def __init__(self, name     , imports                           )        :
        self.name = name
        self.imports = imports

    def check(self)        :
        raise NotImplementedError('check() is not implemented for {}'.format(self.name))

    def apply(self, raw     )       :
        raise NotImplementedError('apply() is not implemented for {}'.format(self.name))
