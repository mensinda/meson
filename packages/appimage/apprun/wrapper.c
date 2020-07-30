#include "common.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// Assume that IS_PYTHON_SCRIPT is either 0 or 1
#ifndef IS_PYTHON_SCRIPT
#define IS_PYTHON_SCRIPT 0
#endif

#ifndef STATICALLY_LINKED
#define STATICALLY_LINKED 0
#endif

int main(int argc, char* argv[]) {
  AppRunInfo_t info;
  char*        args[argc + 3];
  int          counter;

  g_verbose = 0;

  memset(&info, 0, sizeof(info));
  memset(&args, 0, sizeof(args));

  // First sanity check that we are run in an environment set by AppRun
  info.appdir = getenv(VAR_PREFIX "APPDIR");
  if (!info.appdir) {
    DIE("Invalid environment for the " REAL_EXE " wrapper (" VAR_PREFIX
        "APPDIR is not set)");
  }

  // Check for verbose output
  char* verbose = getenv(VAR_PREFIX "VERBOSE");
  if (verbose && verbose[0] != '0') {
    g_verbose = 1;
  }

  info_autofill_paths(&info);

  LOG("Meson exe wrapper " APPRUN_VERSION);
  LOG("Running " REAL_EXE);
  LOG("Extracted AppDir:  %s", info.appdir);
  LOG("Is Python script:  %d", IS_PYTHON_SCRIPT);
  LOG("Statically linked: %d", STATICALLY_LINKED);

  // Set the commandline arguments for exeve
  // Again, IS_PYTHON_SCRIPT and STATICALLY_LINKED must be either 0 or 1
  counter = 2 + IS_PYTHON_SCRIPT - STATICALLY_LINKED;
  for (int i = 1; i < argc; i++) {
    args[counter++] = argv[i];
  }

  args[counter++] = NULL;

#if IS_PYTHON_SCRIPT
  args[0] = info.ld_linux;
  args[1] = absolute(&info, "usr/bin/python3");
  args[2] = absolute(&info, "usr/bin/" REAL_EXE);
#elif STATICALLY_LINKED
  args[0] = absolute(&info, "usr/bin/" REAL_EXE);
#else
  args[0] = info.ld_linux;
  args[1] = absolute(&info, "usr/bin/" REAL_EXE);
#endif

  // Set the env vars
#if !STATICALLY_LINKED
  char* old_ld = getenv("LD_LIBRARY_PATH") ?: "";
  setenv(VAR_PREFIX "LD_LIBRARY_PATH", old_ld, 1);
  envPrepend("LD_LIBRARY_PATH", info.ld_library_path);
#endif

  setenv("PYTHONHOME", info.pythonhome, 1);
  putenv("PYTHONDONTWRITEBYTECODE=1");

  logArgs(args);

  if (execv(args[0], args) != 0) {
    DIE("execv failed");
  }

  // We are technically leaking memory here, but all memory is freed once the
  // program exits anyway...
  return 0;
}
