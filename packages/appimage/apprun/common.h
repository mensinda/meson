#pragma once

// Some global defines to enable functions
#define _XOPEN_SOURCE 500
#define _DEFAULT_SOURCE
#define _BSD_SOURCE
#define _GNU_SOURCE

#define VAR_PREFIX "MESON_AppRun_"
#define FAKEBIN "fakebin"

extern int g_verbose;

#define LOG(fmt, ...)                                                          \
  if (g_verbose) {                                                             \
    printf(fmt "\n", ##__VA_ARGS__);                                           \
    fflush(stdout);                                                            \
  }

#define DIE(fmt, ...)                                                          \
  {                                                                            \
    fprintf(stderr, "\x1b[31;1mFATAL ERROR:\x1b[0;1m " fmt "\x1b[0m\n",        \
            ##__VA_ARGS__);                                                    \
    exit(1);                                                                   \
  }

typedef struct AppRunInfo {
  char* appdir;
  char* appimage_path;

  // basic path inf
  char* path;
  char* ld_linux;
  char* ld_library_path;
  char* pythonhome;
} AppRunInfo_t;

void info_autofill_paths(AppRunInfo_t* inf);

char* absolute(AppRunInfo_t* inf, const char* relpath);
void  envPrepend(const char* var, const char* val);

void logArgs(char** args);
