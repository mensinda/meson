#include "common.h"

#include <libgen.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

void print_help(char* argv0) {
  printf("Usage %s [AppRun/AppImage options] [program options]\n\n", argv0);
  printf("All AppRun and AppImage options start with the --apprun and\n"
         "--appimage prefix and are NOT passed to the selected binary.\n\n"
         "The Meson program is executed by default, however, this can\n"
         "be changed by choosing a different program selector. See the\n"
         "list below for all supported options.\n\n"
         "See --appimage-help for all supported AppImage runtime flags.\n\n"
         "AppRun options:\n");
  printf("  --apprun-help         | Print this help message and exit\n");
  printf("  --apprun-version      | Print the AppRun version and exit\n");
#ifndef DISABLE_LOG
  printf("  --apprun-verbose      | Enable verbose logging (AppRun only)\n");
#endif
  printf("\nProgram selectors:\n");
  printf("  --apprun-meson        | Call meson [default]\n");
  printf("  --apprun-ninja        | Call ninja\n");
  printf("  --apprun-cmake        | Call CMake\n");
  printf("  --apprun-pkg-config   | Call pkg-config\n");
  printf("  --apprun-python3      | Call python\n");
  printf("\n");
}

int main(int argc, char* argv[]) {
  AppRunInfo_t info;
  char*        prog = FAKEBIN "/meson";
  char*        args[argc + 1];

  g_verbose = 0;

  memset(&info, 0, sizeof(info));
  memset(&args, 0, sizeof(args));

  info.appdir        = dirname(realpath("/proc/self/exe", NULL));
  info.appimage_path = realpath(argv[0], NULL);

  if (!info.appdir) {
    DIE("Could not access /proc/self/exe");
  }

  info_autofill_paths(&info);

  // Parse --apprun args
  int i = 1;
  for (; i < argc; i++) {
    if (strncmp(argv[i], "--apprun", 8) != 0) {
      break;
    }

    if (strcmp(argv[i], "--apprun-help") == 0) {
      print_help(argv[0]);
      exit(EXIT_SUCCESS);
    } else if (strcmp(argv[i], "--apprun-version") == 0) {
      printf("%s\n", APPRUN_VERSION);
      exit(EXIT_SUCCESS);
    } else if (strcmp(argv[i], "--apprun-verbose") == 0) {
      g_verbose = 1;
    } else if (strcmp(argv[i], "--apprun-meson") == 0) {
      prog = FAKEBIN "/meson";
    } else if (strcmp(argv[i], "--apprun-ninja") == 0) {
      prog = FAKEBIN "/ninja";
    } else if (strcmp(argv[i], "--apprun-cmake") == 0) {
      prog = FAKEBIN "/cmake";
    } else if (strcmp(argv[i], "--apprun-pkg-config") == 0) {
      prog = FAKEBIN "/pkg-config";
    } else if (strcmp(argv[i], "--apprun-python3") == 0) {
      prog = FAKEBIN "/python3";
    } else {
      fprintf(stderr,
              "\x1b[31;1mERROR:\x1b[0;1m Unknown argument '%s'\x1b[0m\n\n",
              argv[i]);
      print_help(argv[0]);
      exit(1);
    }
  }

  // Copy the remaining args
  unsigned int counter = 1;
  for (; i < argc; i++) {
    args[counter++] = argv[i];
  }

  args[0]         = absolute(&info, prog);
  args[counter++] = NULL;

  LOG("Meson AppRun %s", APPRUN_VERSION);
  LOG("Selected %s", prog);
  LOG("");
  LOG("AppDir:   %s", info.appdir);
  LOG("AppImage: %s", info.appimage_path);

  // Setup env vars
  setenv(VAR_PREFIX "APPDIR", info.appdir, 1);
  setenv(VAR_PREFIX "APPIMAGE", info.appimage_path, 1);
  envPrepend("PATH", info.path); // Set PATH for all apps

  if (g_verbose) {
    putenv(VAR_PREFIX "VERBOSE=1");
  }

  logArgs(args);

  if (execv(args[0], args) != 0) {
    DIE("execv failed");
  }

  // We are technically leaking memory here, but all memory is freed once the
  // program exits anyway...
  return 0;
}
