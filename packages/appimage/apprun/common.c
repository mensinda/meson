#include "common.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int g_verbose;

void info_autofill_paths(AppRunInfo_t* info) {
  if (!info || !info->appdir) {
    DIE("invalid argument to info_autofill_paths");
  }

  info->path            = absolute(info, FAKEBIN);
  info->ld_linux        = absolute(info, "usr/lib/ld-linux.so");
  info->ld_library_path = absolute(info, "usr/lib");
  info->pythonhome      = absolute(info, "usr");
}

void logArgs(char** args) {
  if (!g_verbose) {
    return;
  }

  int counter = 0;
  printf("\nArguments:\n");
  counter = 0;
  while (1) {
    if (!args[counter]) {
      break;
    }
    printf(" %2d: %s\n", counter, args[counter]);
    counter++;
  }

  printf("\n");
  fflush(stdout);
}

char* absolute(AppRunInfo_t* info, const char* relpath) {
  const size_t absLen = strlen(info->appdir) + strlen(relpath) + 2;
  char*        abs    = malloc(sizeof(char) * absLen);
  snprintf(abs, absLen, "%s/%s", info->appdir, relpath);
  return abs;
}

void envPrepend(const char* var, const char* val) {
  char* curr = getenv(var);
  if (!curr) {
    setenv(var, val, 1);
    return;
  }

  const size_t len = strlen(var) + strlen(val) + strlen(curr) + 3;
  char*        res = malloc(sizeof(char) * len);
  snprintf(res, len, "%s=%s:%s", var, val, curr);
  putenv(res);
}
