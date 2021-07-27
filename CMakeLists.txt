# CMakeLists.txt - CMake lists for libpng
#
# Copyright (c) 2018-2025 Cosmin Truta
# Copyright (c) 2007-2018 Glenn Randers-Pehrson
# Originally written by Christian Ehrlicher, 2007
# Copyright (C) 2015 Ruslan Baratov
#
# Use, modification and distribution are subject to
# the same licensing terms and conditions as libpng.
# Please see the copyright notice in png.h or visit
# http://libpng.org/pub/png/src/libpng-LICENSE.txt
#
# For copyright and licensing purposes, please see
# the accompanying file scripts/cmake/AUTHORS.md
#
# SPDX-License-Identifier: libpng-2.0

cmake_minimum_required(VERSION 3.14)

# Don't complain about endif() etc mismatches
set(CMAKE_ALLOW_LOOSE_LOOP_CONSTRUCTS true)

include("cmake/HunterGate.cmake")
HunterGate(
    URL "https://github.com/ruslo/hunter/archive/v0.23.152.tar.gz"
    SHA1 "0c9801f60a8149c3105db04501bbcfb155581b7d"
)

set(PNGLIB_MAJOR 1)
set(PNGLIB_MINOR 6)
set(PNGLIB_REVISION 47)
set(PNGLIB_SUBREVISION 0)
#set(PNGLIB_SUBREVISION "git")
set(PNGLIB_VERSION ${PNGLIB_MAJOR}.${PNGLIB_MINOR}.${PNGLIB_REVISION})
set(PNGLIB_ABI_VERSION ${PNGLIB_MAJOR}${PNGLIB_MINOR})
set(PNGLIB_SHARED_VERSION ${PNGLIB_ABI_VERSION}.${PNGLIB_REVISION}.${PNGLIB_SUBREVISION})

project(libpng
        VERSION ${PNGLIB_VERSION}
        LANGUAGES C ASM)

include(CheckCSourceCompiles)
include(GNUInstallDirs)

# Allow the users to specify an application-specific API prefix for libpng
# vendoring purposes. A standard libpng build should have no such prefix.
set(PNG_PREFIX ""
    CACHE STRING "Prefix to prepend to the API function names")

# Allow the users to override the postfix appended to debug library file names.
# Previously, we used to set CMAKE_DEBUG_POSTFIX globally. That variable should
# not be cached, however, because doing so would affect all projects processed
# after libpng, in unexpected and undesirable ways.
set(PNG_DEBUG_POSTFIX "d"
    CACHE STRING "Postfix to append to library file names under the Debug configuration")

# Allow the users to import their own extra configuration settings.
set(DFA_XTRA ""
    CACHE FILEPATH "File containing extra configuration settings")

if(APPLE)
  option(PNG_FRAMEWORK "Build libpng as a framework bundle" OFF)
endif()

# Allow the users to switch on/off the auxiliary build and test artifacts.
# These artifacts are NOT part of libpng proper, and are subject to change
# at any time.
option(PNG_TESTS "Build the libpng tests" OFF)

# Same as above, but for the third-party tools.
# Although these tools are targetted at development environments only,
# the users are allowed to override the option to build by default.
if(ANDROID OR IOS)
  option(PNG_TOOLS "Build the libpng tools" OFF)
else()
  option(PNG_TOOLS "Build the libpng tools" OFF)
endif()

# Maintain backwards compatibility with the deprecated option PNG_EXECUTABLES.
option(PNG_EXECUTABLES "[Deprecated; please use PNG_TOOLS]" ON)
if(NOT PNG_EXECUTABLES)
  message(DEPRECATION "The option PNG_EXECUTABLES has been deprecated in favour of PNG_TOOLS")
  if(PNG_TOOLS)
    message(AUTHOR_WARNING
            "Setting PNG_TOOLS to ${PNG_EXECUTABLES}, to stay compatible with PNG_EXECUTABLES")
    set(PNG_TOOLS "${PNG_EXECUTABLES}")
  endif()
endif()

# Allow the users to configure various compilation options.
option(PNG_DEBUG "Enable debug output" OFF)
option(PNG_HARDWARE_OPTIMIZATIONS "Enable hardware optimizations" ON)

option(PNG_DISABLE_AWK "Disable AWK based scripts code generation" YES)

# Initialize and show the target architecture variable PNG_TARGET_ARCHITECTURE.
#
# NOTE:
# On macOS, CMake sets CMAKE_SYSTEM_PROCESSOR to either "x86_64" or "arm64",
# based upon the OS architecture, not the target architecture. As such, we need
# to check CMAKE_OSX_ARCHITECTURES to identify which hardware-specific flags to
# enable. Note that this will fail if you attempt to build a universal binary
# in a single CMake invocation.
if(APPLE AND CMAKE_OSX_ARCHITECTURES)
  string(TOLOWER "${CMAKE_OSX_ARCHITECTURES}" PNG_TARGET_ARCHITECTURE)
else()
  string(TOLOWER "${CMAKE_SYSTEM_PROCESSOR}" PNG_TARGET_ARCHITECTURE)
endif()
message(STATUS "Building for target architecture: ${PNG_TARGET_ARCHITECTURE}")

if(NOT CMAKE_VERSION VERSION_LESS 3.12)
  # For CMake >= 3.12, find_package(<PackageName>) searches prefixes given by
  # <PackageName>_ROOT CMake variable and <PackageName>_ROOT
  # environment variable.
  cmake_policy(SET CMP0074 NEW)
endif()
hunter_add_package(ZLIB)
find_package(ZLIB CONFIG REQUIRED)

if(UNIX
   AND NOT (APPLE OR BEOS OR HAIKU)
   AND NOT EMSCRIPTEN)
  find_library(M_LIBRARY m)
  if(M_LIBRARY)
    set(M_LIBRARY m)
  else()
    set(M_LIBRARY "")
  endif()
else()
  # libm is not available or not needed.
endif()

if(APPLE)
  # If IOS is not set, check CMAKE_OSX_ROOT
  if(NOT IOS)
    if(CMAKE_OSX_SYSROOT STREQUAL "iphoneos")
      set(IOS ON)
    endif()
  endif()
endif()

if(IOS AND CMAKE_SYSTEM_PROCESSOR STREQUAL "")
  # In multi-architecture IOS builds, the CMAKE_SYSTEM_PROCESSOR
  # field is blank. The PNG_HARDWARE_OPTIMIZATIONS statement below
  # can't cope with this as such. Disable optimisations and ensure
  # flags are set properly in the else part below.
  SET(PNG_HARDWARE_OPTIMIZATIONS OFF)
endif()

if(PNG_HARDWARE_OPTIMIZATIONS)

  # Set definitions and sources for ARM.
  if(PNG_TARGET_ARCHITECTURE MATCHES "^(arm|aarch)")
    if(PNG_TARGET_ARCHITECTURE MATCHES "^(arm64|aarch64)")
      set(PNG_ARM_NEON_POSSIBLE_VALUES on off)
      set(PNG_ARM_NEON "on"
          CACHE STRING "Enable ARM NEON optimizations: on|off; on is default")
    else()
      set(PNG_ARM_NEON_POSSIBLE_VALUES check on off)
       if(IOS)
         set(neon_default "off")
       else()
         set(neon_default "check")
       endif()
       message("****neon_default: ${neon_default}")
       set(PNG_ARM_NEON "${neon_default}"
          CACHE STRING "Enable ARM NEON optimizations: check|on|off; off is default")
    endif()
    set_property(CACHE PNG_ARM_NEON
                PROPERTY STRINGS ${PNG_ARM_NEON_POSSIBLE_VALUES})
    list(FIND PNG_ARM_NEON_POSSIBLE_VALUES ${PNG_ARM_NEON} index)
    if(index EQUAL -1)
      message(FATAL_ERROR "PNG_ARM_NEON must be one of [${PNG_ARM_NEON_POSSIBLE_VALUES}]")
    elseif(NOT PNG_ARM_NEON STREQUAL "off")
      set(libpng_arm_sources
          arm/arm_init.c
          arm/filter_neon_intrinsics.c
          arm/palette_neon_intrinsics.c)
      if(PNG_ARM_NEON STREQUAL "on")
        add_definitions(-DPNG_ARM_NEON_OPT=2)
      elseif(PNG_ARM_NEON STREQUAL "check")
        add_definitions(-DPNG_ARM_NEON_CHECK_SUPPORTED)
      endif()
    else()
      add_definitions(-DPNG_ARM_NEON_OPT=0)
    endif()
  endif()

  # Set definitions and sources for PowerPC.
  if(PNG_TARGET_ARCHITECTURE MATCHES "^(powerpc|ppc64)")
    set(PNG_POWERPC_VSX_POSSIBLE_VALUES on off)
    set(PNG_POWERPC_VSX "on"
        CACHE STRING "Enable POWERPC VSX optimizations: on|off; on is default")
    set_property(CACHE PNG_POWERPC_VSX
                PROPERTY STRINGS ${PNG_POWERPC_VSX_POSSIBLE_VALUES})
    list(FIND PNG_POWERPC_VSX_POSSIBLE_VALUES ${PNG_POWERPC_VSX} index)
    if(index EQUAL -1)
      message(FATAL_ERROR "PNG_POWERPC_VSX must be one of [${PNG_POWERPC_VSX_POSSIBLE_VALUES}]")
    elseif(NOT PNG_POWERPC_VSX STREQUAL "off")
      set(libpng_powerpc_sources
          powerpc/powerpc_init.c
          powerpc/filter_vsx_intrinsics.c)
      if(PNG_POWERPC_VSX STREQUAL "on")
        add_definitions(-DPNG_POWERPC_VSX_OPT=2)
      endif()
    else()
      add_definitions(-DPNG_POWERPC_VSX_OPT=0)
    endif()
  endif()

  # Set definitions and sources for Intel.
  if(PNG_TARGET_ARCHITECTURE MATCHES "^(i[3-6]86|x86|amd64)")
    set(PNG_INTEL_SSE_POSSIBLE_VALUES on off)
    set(PNG_INTEL_SSE "on"
        CACHE STRING "Enable INTEL_SSE optimizations: on|off; on is default")
    set_property(CACHE PNG_INTEL_SSE
                PROPERTY STRINGS ${PNG_INTEL_SSE_POSSIBLE_VALUES})
    list(FIND PNG_INTEL_SSE_POSSIBLE_VALUES ${PNG_INTEL_SSE} index)
    if(index EQUAL -1)
      message(FATAL_ERROR "PNG_INTEL_SSE must be one of [${PNG_INTEL_SSE_POSSIBLE_VALUES}]")
    elseif(NOT PNG_INTEL_SSE STREQUAL "off")
      set(libpng_intel_sources
          intel/intel_init.c
          intel/filter_sse2_intrinsics.c)
      if(PNG_INTEL_SSE STREQUAL "on")
        add_definitions(-DPNG_INTEL_SSE_OPT=1)
      endif()
    else()
      add_definitions(-DPNG_INTEL_SSE_OPT=0)
    endif()
  endif()

  # Set definitions and sources for MIPS.
  if(PNG_TARGET_ARCHITECTURE MATCHES "^(mipsel|mips64el)")
    set(PNG_MIPS_MSA_POSSIBLE_VALUES on off)
    set(PNG_MIPS_MSA "on"
        CACHE STRING "Enable MIPS_MSA optimizations: on|off; on is default")
    set_property(CACHE PNG_MIPS_MSA
                PROPERTY STRINGS ${PNG_MIPS_MSA_POSSIBLE_VALUES})
    list(FIND PNG_MIPS_MSA_POSSIBLE_VALUES ${PNG_MIPS_MSA} index_msa)
    if(index_msa EQUAL -1)
      message(FATAL_ERROR "PNG_MIPS_MSA must be one of [${PNG_MIPS_MSA_POSSIBLE_VALUES}]")
    endif()

    set(PNG_MIPS_MMI_POSSIBLE_VALUES on off)
    set(PNG_MIPS_MMI "on"
        CACHE STRING "Enable MIPS_MMI optimizations: on|off; on is default")
    set_property(CACHE PNG_MIPS_MMI
                PROPERTY STRINGS ${PNG_MIPS_MMI_POSSIBLE_VALUES})
    list(FIND PNG_MIPS_MMI_POSSIBLE_VALUES ${PNG_MIPS_MMI} index_mmi)
    if(index_mmi EQUAL -1)
      message(FATAL_ERROR "PNG_MIPS_MMI must be one of [${PNG_MIPS_MMI_POSSIBLE_VALUES}]")
    endif()

    if(PNG_MIPS_MSA STREQUAL "on" AND PNG_MIPS_MMI STREQUAL "on")
      set(libpng_mips_sources
          mips/mips_init.c
          mips/filter_msa_intrinsics.c
          mips/filter_mmi_inline_assembly.c)
      add_definitions(-DPNG_MIPS_MSA_OPT=2)
      add_definitions(-DPNG_MIPS_MMI_OPT=1)
    elseif(PNG_MIPS_MSA STREQUAL "on")
      set(libpng_mips_sources
          mips/mips_init.c
          mips/filter_msa_intrinsics.c)
      add_definitions(-DPNG_MIPS_MSA_OPT=2)
      add_definitions(-DPNG_MIPS_MMI_OPT=0)
    elseif(PNG_MIPS_MMI STREQUAL "on")
      set(libpng_mips_sources
          mips/mips_init.c
          mips/filter_mmi_inline_assembly.c)
      add_definitions(-DPNG_MIPS_MSA_OPT=0)
      add_definitions(-DPNG_MIPS_MMI_OPT=1)
    else()
      add_definitions(-DPNG_MIPS_MSA_OPT=0)
      add_definitions(-DPNG_MIPS_MMI_OPT=0)
    endif()
  endif()

  # Set definitions and sources for LoongArch.
  if(PNG_TARGET_ARCHITECTURE MATCHES "^(loongarch)")
    include(CheckCCompilerFlag)
    set(PNG_LOONGARCH_LSX_POSSIBLE_VALUES on off)
    set(PNG_LOONGARCH_LSX "on"
        CACHE STRING "Enable LOONGARCH_LSX optimizations: on|off; on is default")
    set_property(CACHE PNG_LOONGARCH_LSX
                PROPERTY STRINGS ${PNG_LOONGARCH_LSX_POSSIBLE_VALUES})
    list(FIND PNG_LOONGARCH_LSX_POSSIBLE_VALUES ${PNG_LOONGARCH_LSX} index)
    if(index EQUAL -1)
      message(FATAL_ERROR "PNG_LOONGARCH_LSX must be one of [${PNG_LOONGARCH_LSX_POSSIBLE_VALUES}]")
    elseif(NOT PNG_LOONGARCH_LSX STREQUAL "off")
      CHECK_C_COMPILER_FLAG("-mlsx" COMPILER_SUPPORTS_LSX)
      if(COMPILER_SUPPORTS_LSX)
        set(libpng_loongarch_sources
            loongarch/loongarch_lsx_init.c
            loongarch/filter_lsx_intrinsics.c)
        set_source_files_properties(${libpng_loongarch_sources}
                                    PROPERTIES
                                    COMPILE_FLAGS "-mlsx")
        add_definitions(-DPNG_LOONGARCH_LSX_OPT=1)
      else()
        message(FATAL_ERROR "Compiler does not support -mlsx option")
      endif()
    else()
      add_definitions(-DPNG_LOONGARCH_LSX_OPT=0)
    endif()
  endif()

else(PNG_HARDWARE_OPTIMIZATIONS)

  # Set definitions and sources for ARM.
  if(PNG_TARGET_ARCHITECTURE MATCHES "^(arm|aarch)")
    add_definitions(-DPNG_ARM_NEON_OPT=0)
  endif()

  # Set definitions and sources for PowerPC.
  if(PNG_TARGET_ARCHITECTURE MATCHES "^(powerpc|ppc64)")
    add_definitions(-DPNG_POWERPC_VSX_OPT=0)
  endif()

  # Set definitions and sources for Intel.
  if(PNG_TARGET_ARCHITECTURE MATCHES "^(i[3-6]86|x86|amd64)")
    add_definitions(-DPNG_INTEL_SSE_OPT=0)
  endif()

  # Set definitions and sources for MIPS.
  if(PNG_TARGET_ARCHITECTURE MATCHES "^(mipsel|mips64el)")
    add_definitions(-DPNG_MIPS_MSA_OPT=0)
  endif()

  # Set definitions and sources for LoongArch.
  if(PNG_TARGET_ARCHITECTURE MATCHES "^(loongarch)")
    add_definitions(-DPNG_LOONGARCH_LSX_OPT=0)
  endif()

endif(PNG_HARDWARE_OPTIMIZATIONS)

option(ld-version-script "Enable linker version script" ON)
if(ld-version-script AND NOT (ANDROID OR APPLE))
  # Check if LD supports linker scripts.
  file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/conftest.map" "
VERS_1 { global: sym1; local: *; };
VERS_2 { global: sym2; main; } VERS_1;
")
  set(_SAVED_CMAKE_REQUIRED_FLAGS ${CMAKE_REQUIRED_FLAGS})
  if(NOT CMAKE_HOST_SOLARIS)
    # Avoid using CMAKE_SHARED_LIBRARY_C_FLAGS in version script checks on
    # Solaris, because of an incompatibility with the Solaris link editor.
    list(APPEND CMAKE_REQUIRED_FLAGS ${CMAKE_SHARED_LIBRARY_C_FLAGS})
  endif()
  list(APPEND CMAKE_REQUIRED_FLAGS "-Wl,--version-script='${CMAKE_CURRENT_BINARY_DIR}/conftest.map'")
  check_c_source_compiles("
void sym1(void) {}
void sym2(void) {}
int main(void) { return 0; }
" HAVE_LD_VERSION_SCRIPT)
  if(NOT HAVE_LD_VERSION_SCRIPT)
    set(CMAKE_REQUIRED_FLAGS ${_SAVED_CMAKE_REQUIRED_FLAGS})
    if(NOT CMAKE_HOST_SOLARIS)
      # Again, avoid using CMAKE_SHARED_LIBRARY_C_FLAGS in version script
      # checks on Solaris.
      list(APPEND CMAKE_REQUIRED_FLAGS ${CMAKE_SHARED_LIBRARY_C_FLAGS})
    endif()
    list(APPEND CMAKE_REQUIRED_FLAGS "-Wl,-M -Wl,${CMAKE_CURRENT_BINARY_DIR}/conftest.map")
    check_c_source_compiles("
void sym1(void) {}
void sym2(void) {}
int main(void) { return 0; }
" HAVE_SOLARIS_LD_VERSION_SCRIPT)
  endif()
  set(CMAKE_REQUIRED_FLAGS ${_SAVED_CMAKE_REQUIRED_FLAGS})
  file(REMOVE "${CMAKE_CURRENT_BINARY_DIR}/conftest.map")
endif()

# Find an AWK language processor.
# Start with specific AWK implementations like gawk and nawk, which are
# known to work with our scripts, then fall back to the system awk.
find_program(AWK NAMES gawk nawk awk)
if(AWK)
  message(STATUS "Found AWK program: ${AWK}")
else()
  message(STATUS "Could not find an AWK-compatible program")
endif()

if(NOT AWK OR (ANDROID OR IOS) OR PNG_DISABLE_AWK)
  # No awk available to generate sources; use pre-built pnglibconf.h
  configure_file(${CMAKE_CURRENT_SOURCE_DIR}/scripts/pnglibconf.h.prebuilt
                 ${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.h)
  add_custom_target(png_genfiles)
else()
  # Include the internal module PNGGenConfig.cmake
  include(${CMAKE_CURRENT_SOURCE_DIR}/scripts/cmake/PNGGenConfig.cmake)

  # Copy the awk scripts, converting their line endings to Unix (LF)
  configure_file(${CMAKE_CURRENT_SOURCE_DIR}/scripts/checksym.awk
                 ${CMAKE_CURRENT_BINARY_DIR}/scripts/checksym.awk
                 @ONLY
                 NEWLINE_STYLE LF)
  configure_file(${CMAKE_CURRENT_SOURCE_DIR}/scripts/options.awk
                 ${CMAKE_CURRENT_BINARY_DIR}/scripts/options.awk
                 @ONLY
                 NEWLINE_STYLE LF)
  configure_file(${CMAKE_CURRENT_SOURCE_DIR}/scripts/dfn.awk
                 ${CMAKE_CURRENT_BINARY_DIR}/scripts/dfn.awk
                 @ONLY
                 NEWLINE_STYLE LF)

  # Generate scripts/pnglibconf.h
  generate_source(OUTPUT "scripts/pnglibconf.c"
                  DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/scripts/pnglibconf.dfa"
                          "${CMAKE_CURRENT_BINARY_DIR}/scripts/options.awk"
                          "${CMAKE_CURRENT_SOURCE_DIR}/pngconf.h")
  add_custom_target(png_scripts_pnglibconf_c
                    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/scripts/pnglibconf.c")

  # Generate pnglibconf.c
  generate_source(OUTPUT "pnglibconf.c"
                  DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/scripts/pnglibconf.dfa"
                          "${CMAKE_CURRENT_BINARY_DIR}/scripts/options.awk"
                          "${CMAKE_CURRENT_SOURCE_DIR}/pngconf.h")
  add_custom_target(pnglibconf_c
                    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.c")

  if(PNG_PREFIX)
    set(PNGLIBCONF_H_EXTRA_DEPENDS
        "${CMAKE_CURRENT_BINARY_DIR}/scripts/prefix.out"
        "${CMAKE_CURRENT_SOURCE_DIR}/scripts/macro.lst")
    set(PNGPREFIX_H_EXTRA_DEPENDS
        "${CMAKE_CURRENT_BINARY_DIR}/scripts/intprefix.out")
  endif()

  generate_out(INPUT "${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.c"
               OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.out"
               DEPENDS pnglibconf_c)
  add_custom_target(pnglibconf_out
                    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.out")

  # Generate pnglibconf.h
  generate_source(OUTPUT "pnglibconf.h"
                  DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.out" pnglibconf_out
                          ${PNGLIBCONF_H_EXTRA_DEPENDS})
  add_custom_target(pnglibconf_h
                    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.h")

  generate_out(INPUT "${CMAKE_CURRENT_SOURCE_DIR}/scripts/intprefix.c"
               OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/scripts/intprefix.out"
               DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.h" pnglibconf_h)
  add_custom_target(png_scripts_intprefix_out
                    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/scripts/intprefix.out")

  generate_out(INPUT "${CMAKE_CURRENT_SOURCE_DIR}/scripts/prefix.c"
               OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/scripts/prefix.out"
               DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/png.h"
                       "${CMAKE_CURRENT_SOURCE_DIR}/pngconf.h"
                       "${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.out" pnglibconf_out)
  add_custom_target(png_scripts_prefix_out
                    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/scripts/prefix.out")

  # Generate pngprefix.h
  generate_source(OUTPUT "pngprefix.h"
                  DEPENDS ${PNGPREFIX_H_EXTRA_DEPENDS})
  add_custom_target(pngprefix_h
                    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/pngprefix.h")

  generate_out(INPUT "${CMAKE_CURRENT_SOURCE_DIR}/scripts/sym.c"
               OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/scripts/sym.out"
               DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.h" pnglibconf_h)
  add_custom_target(png_scripts_sym_out
                    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/scripts/sym.out")

  generate_out(INPUT "${CMAKE_CURRENT_SOURCE_DIR}/scripts/symbols.c"
               OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/scripts/symbols.out"
               DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/png.h"
                       "${CMAKE_CURRENT_SOURCE_DIR}/pngconf.h"
                       "${CMAKE_CURRENT_SOURCE_DIR}/scripts/pnglibconf.h.prebuilt")
  add_custom_target(png_scripts_symbols_out
                    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/scripts/symbols.out")

  generate_out(INPUT "${CMAKE_CURRENT_SOURCE_DIR}/scripts/vers.c"
               OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/scripts/vers.out"
               DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/png.h"
                       "${CMAKE_CURRENT_SOURCE_DIR}/pngconf.h"
                       "${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.h" pnglibconf_h)
  add_custom_target(png_scripts_vers_out
                    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/scripts/vers.out")

  generate_chk(INPUT "${CMAKE_CURRENT_BINARY_DIR}/scripts/symbols.out"
               OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/scripts/symbols.chk"
               DEPENDS png_scripts_symbols_out
                       "${CMAKE_CURRENT_BINARY_DIR}/scripts/checksym.awk"
                       "${CMAKE_CURRENT_SOURCE_DIR}/scripts/symbols.def")

  add_custom_target(png_scripts_symbols_chk
                    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/scripts/symbols.chk")

  generate_copy(INPUT "${CMAKE_CURRENT_BINARY_DIR}/scripts/sym.out"
                OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/libpng.sym"
                DEPENDS png_scripts_sym_out)
  generate_copy(INPUT "${CMAKE_CURRENT_BINARY_DIR}/scripts/vers.out"
                OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/libpng.vers"
                DEPENDS png_scripts_vers_out)

  add_custom_target(png_genvers
                    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/libpng.vers")
  add_custom_target(png_gensym
                    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/libpng.sym")

  add_custom_target(png_genprebuilt
                    COMMAND "${CMAKE_COMMAND}"
                            "-DOUTPUT=scripts/pnglibconf.h.prebuilt"
                            -P "${CMAKE_CURRENT_BINARY_DIR}/scripts/cmake/gensrc.cmake"
                    WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}")

  # A single target handles generation of all generated files.
  add_custom_target(png_genfiles
                    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/libpng.sym" png_gensym
                            "${CMAKE_CURRENT_BINARY_DIR}/libpng.vers" png_genvers
                            "${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.c" pnglibconf_c
                            "${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.h" pnglibconf_h
                            "${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.out" pnglibconf_out
                            "${CMAKE_CURRENT_BINARY_DIR}/pngprefix.h" pngprefix_h
                            "${CMAKE_CURRENT_BINARY_DIR}/scripts/intprefix.out" png_scripts_intprefix_out
                            "${CMAKE_CURRENT_BINARY_DIR}/scripts/pnglibconf.c" png_scripts_pnglibconf_c
                            "${CMAKE_CURRENT_BINARY_DIR}/scripts/prefix.out" png_scripts_prefix_out
                            "${CMAKE_CURRENT_BINARY_DIR}/scripts/sym.out" png_scripts_sym_out
                            "${CMAKE_CURRENT_BINARY_DIR}/scripts/symbols.chk" png_scripts_symbols_chk
                            "${CMAKE_CURRENT_BINARY_DIR}/scripts/symbols.out" png_scripts_symbols_out
                            "${CMAKE_CURRENT_BINARY_DIR}/scripts/vers.out" png_scripts_vers_out)
endif(NOT AWK OR (ANDROID OR IOS) OR PNG_DISABLE_AWK)

# List the source code files.
set(libpng_public_hdrs
    png.h
    pngconf.h
    "${CMAKE_CURRENT_BINARY_DIR}/pnglibconf.h"
)
set(libpng_private_hdrs
    pngpriv.h
    pngdebug.h
    pnginfo.h
    pngstruct.h
)
if(AWK AND NOT (ANDROID OR IOS) AND NOT PNG_DISABLE_AWK)
  list(APPEND libpng_private_hdrs "${CMAKE_CURRENT_BINARY_DIR}/pngprefix.h")
endif()
set(libpng_sources
    ${libpng_public_hdrs}
    ${libpng_private_hdrs}
    png.c
    pngerror.c
    pngget.c
    pngmem.c
    pngpread.c
    pngread.c
    pngrio.c
    pngrtran.c
    pngrutil.c
    pngset.c
    pngtrans.c
    pngwio.c
    pngwrite.c
    pngwtran.c
    pngwutil.c
    ${libpng_arm_sources}
    ${libpng_intel_sources}
    ${libpng_mips_sources}
    ${libpng_powerpc_sources}
    ${libpng_loongarch_sources}
)
set(pngtest_sources
    pngtest.c
)
set(pngvalid_sources
    contrib/libtests/pngvalid.c
)
set(pngstest_sources
    contrib/libtests/pngstest.c
)
set(pngunknown_sources
    contrib/libtests/pngunknown.c
)
set(pngimage_sources
    contrib/libtests/pngimage.c
)
set(pngfix_sources
    contrib/tools/pngfix.c
)
set(png_fix_itxt_sources
    contrib/tools/png-fix-itxt.c
)

if(MSVC OR (WIN32 AND (CMAKE_C_COMPILER_ID MATCHES "Clang")))
  add_definitions(-D_CRT_NONSTDC_NO_DEPRECATE)
  add_definitions(-D_CRT_SECURE_NO_DEPRECATE)
endif()

if(PNG_DEBUG)
  add_definitions(-DPNG_DEBUG)
endif()

# Now build our targets.
add_library(png ${libpng_sources})

if("${CMAKE_SYSTEM_NAME}" STREQUAL "WindowsStore")
  # ExitProcess not available
  target_compile_definitions(png PRIVATE -DPNG_WINDOWS_STORE)
elseif(MSVC)
  # ExitProcess
  target_link_libraries(png PUBLIC Kernel32)
endif()

if(PNG_FRAMEWORK AND NOT APPLE)
  message(AUTHOR_WARNING
          "Setting PNG_FRAMEWORK to OFF, as it only applies to Apple systems")
  set(PNG_FRAMEWORK OFF)
endif()

if(PNG_FRAMEWORK)
  add_library(png_framework SHARED ${libpng_sources})
  add_dependencies(png_framework png_genfiles)
  list(APPEND PNG_LIBRARY_TARGETS png_framework)
  set_target_properties(png_framework PROPERTIES
                        FRAMEWORK TRUE
                        FRAMEWORK_VERSION "${PNGLIB_VERSION}"
                        MACOSX_FRAMEWORK_SHORT_VERSION_STRING "${PNGLIB_MAJOR}.${PNGLIB_MINOR}"
                        MACOSX_FRAMEWORK_BUNDLE_VERSION "${PNGLIB_VERSION}"
                        MACOSX_FRAMEWORK_IDENTIFIER "org.libpng.libpng"
                        XCODE_ATTRIBUTE_INSTALL_PATH "@rpath"
                        PUBLIC_HEADER "${libpng_public_hdrs}"
                        OUTPUT_NAME "png"
                        DEBUG_POSTFIX "${PNG_DEBUG_POSTFIX}")
  # Avoid CMake's implicit compile definition "-Dpng_framework_EXPORTS".
  set_target_properties(png_framework PROPERTIES DEFINE_SYMBOL "")
  target_include_directories(png_framework
                             PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>)
  target_include_directories(png_framework
                             PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}>)
  target_include_directories(png_framework SYSTEM
                             INTERFACE $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/libpng${PNGLIB_ABI_VERSION}>)
  target_link_libraries(png_framework PRIVATE ZLIB::zlib ${M_LIBRARY})
endif()

target_link_libraries(png PRIVATE ZLIB::zlib ${M_LIBRARY})

target_compile_definitions(png PUBLIC "$<$<CONFIG:Debug>:PNG_DEBUG>")

if(PNG_TESTS)
  enable_testing()

  # Include the internal module PNGTest.cmake
  include(${CMAKE_CURRENT_SOURCE_DIR}/scripts/cmake/PNGTest.cmake)

  # Find test PNG files by globbing, but sort lists to ensure
  # consistency between different filesystems.
  file(GLOB PNGSUITE_PNGS "${CMAKE_CURRENT_SOURCE_DIR}/contrib/pngsuite/*.png")
  list(SORT PNGSUITE_PNGS)
  file(GLOB TEST_PNGS "${CMAKE_CURRENT_SOURCE_DIR}/contrib/testpngs/*.png")
  list(SORT TEST_PNGS)
  file(GLOB TEST_PNG3_PNGS "${CMAKE_CURRENT_SOURCE_DIR}/contrib/testpngs/png-3/*.png")
  list(SORT TEST_PNG3_PNGS)

  set(PNGTEST_PNG "${CMAKE_CURRENT_SOURCE_DIR}/pngtest.png")

  add_executable(pngtest ${pngtest_sources})
  target_link_libraries(pngtest PRIVATE png ZLIB::zlib ${M_LIBRARY})

  png_add_test(NAME pngtest
               COMMAND pngtest
               FILES "${PNGTEST_PNG}")

  png_add_test(NAME pngtest-png-3
               COMMAND pngtest
               FILES "${TEST_PNG3_PNGS}")

  add_executable(pngvalid ${pngvalid_sources})
  target_link_libraries(pngvalid PRIVATE png ZLIB::zlib ${M_LIBRARY})

  png_add_test(NAME pngvalid-gamma-16-to-8
               COMMAND pngvalid
               OPTIONS --gamma-16-to-8)
  png_add_test(NAME pngvalid-gamma-alpha-mode
               COMMAND pngvalid
               OPTIONS --gamma-alpha-mode)
  png_add_test(NAME pngvalid-gamma-background
               COMMAND pngvalid
               OPTIONS --gamma-background)
  png_add_test(NAME pngvalid-gamma-expand16-alpha-mode
               COMMAND pngvalid
               OPTIONS --gamma-alpha-mode --expand16)
  png_add_test(NAME pngvalid-gamma-expand16-background
               COMMAND pngvalid
               OPTIONS --gamma-background --expand16)
  png_add_test(NAME pngvalid-gamma-expand16-transform
               COMMAND pngvalid
               OPTIONS --gamma-transform --expand16)
  png_add_test(NAME pngvalid-gamma-sbit
               COMMAND pngvalid
               OPTIONS --gamma-sbit)
  png_add_test(NAME pngvalid-gamma-threshold
               COMMAND pngvalid
               OPTIONS --gamma-threshold)
  png_add_test(NAME pngvalid-gamma-transform
               COMMAND pngvalid
               OPTIONS --gamma-transform)
  png_add_test(NAME pngvalid-progressive-interlace-standard
               COMMAND pngvalid
               OPTIONS --standard --progressive-read --interlace)
  png_add_test(NAME pngvalid-progressive-size
               COMMAND pngvalid
               OPTIONS --size --progressive-read)
  png_add_test(NAME pngvalid-progressive-standard
               COMMAND pngvalid
               OPTIONS --standard --progressive-read)
  png_add_test(NAME pngvalid-standard
               COMMAND pngvalid
               OPTIONS --standard)
  png_add_test(NAME pngvalid-transform
               COMMAND pngvalid
               OPTIONS --transform)

  add_executable(pngstest ${pngstest_sources})
  target_link_libraries(pngstest PRIVATE png ${M_LIBRARY})

  foreach(gamma_type 1.8 linear none sRGB)
    foreach(alpha_type none alpha)
      set(PNGSTEST_FILES)
      foreach(test_png ${TEST_PNGS})
        string(REGEX MATCH "-linear[-.]" TEST_PNG_LINEAR "${test_png}")
        string(REGEX MATCH "-sRGB[-.]" TEST_PNG_SRGB "${test_png}")
        string(REGEX MATCH "-1.8[-.]" TEST_PNG_G18 "${test_png}")
        string(REGEX MATCH "-alpha-" TEST_PNG_ALPHA "${test_png}")

        set(TEST_PNG_VALID TRUE)

        if(TEST_PNG_ALPHA)
          if(NOT alpha_type STREQUAL "alpha")
            set(TEST_PNG_VALID FALSE)
          endif()
        else()
          if(alpha_type STREQUAL "alpha")
            set(TEST_PNG_VALID FALSE)
          endif()
        endif()

        if(TEST_PNG_LINEAR)
          if(NOT gamma_type STREQUAL "linear")
            set(TEST_PNG_VALID FALSE)
          endif()
        elseif(TEST_PNG_SRGB)
          if(NOT gamma_type STREQUAL "sRGB")
            set(TEST_PNG_VALID FALSE)
          endif()
        elseif(TEST_PNG_G18)
          if(NOT gamma_type STREQUAL "1.8")
            set(TEST_PNG_VALID FALSE)
          endif()
        else()
          if(NOT gamma_type STREQUAL "none")
            set(TEST_PNG_VALID FALSE)
          endif()
        endif()

        if(TEST_PNG_VALID)
          list(APPEND PNGSTEST_FILES "${test_png}")
        endif()
      endforeach()
      # Should already be sorted, but sort anyway to be certain.
      list(SORT PNGSTEST_FILES)
      png_add_test(NAME pngstest-${gamma_type}-${alpha_type}
                   COMMAND pngstest
                   OPTIONS --tmpfile "${gamma_type}-${alpha_type}-" --log
                   FILES ${PNGSTEST_FILES})
    endforeach()
  endforeach()

  add_executable(pngunknown ${pngunknown_sources})
  target_link_libraries(pngunknown PRIVATE png ZLIB::zlib ${M_LIBRARY})

  png_add_test(NAME pngunknown-discard
               COMMAND pngunknown
               OPTIONS --strict default=discard
               FILES "${PNGTEST_PNG}")
  png_add_test(NAME pngunknown-IDAT
               COMMAND pngunknown
               OPTIONS --strict default=discard IDAT=save
               FILES "${PNGTEST_PNG}")
  png_add_test(NAME pngunknown-if-safe
               COMMAND pngunknown
               OPTIONS --strict default=if-safe
               FILES "${PNGTEST_PNG}")
  png_add_test(NAME pngunknown-sAPI
               COMMAND pngunknown
               OPTIONS --strict bKGD=save cHRM=save gAMA=save all=discard iCCP=save sBIT=save sRGB=save
               FILES "${PNGTEST_PNG}")
  png_add_test(NAME pngunknown-save
               COMMAND pngunknown
               OPTIONS --strict default=save
               FILES "${PNGTEST_PNG}")
  png_add_test(NAME pngunknown-sTER
               COMMAND pngunknown
               OPTIONS --strict sTER=if-safe
               FILES "${PNGTEST_PNG}")
  png_add_test(NAME pngunknown-vpAg
               COMMAND pngunknown
               OPTIONS --strict vpAg=if-safe
               FILES "${PNGTEST_PNG}")

  add_executable(pngimage ${pngimage_sources})
  target_link_libraries(pngimage PRIVATE png ZLIB::zlib ${M_LIBRARY})

  png_add_test(NAME pngimage-quick
               COMMAND pngimage
               OPTIONS --list-combos --log
               FILES ${PNGSUITE_PNGS})
  png_add_test(NAME pngimage-full
               COMMAND pngimage
               OPTIONS --exhaustive --list-combos --log
               FILES ${PNGSUITE_PNGS})
endif()

if(PNG_TOOLS)
  add_executable(pngfix ${pngfix_sources})
  target_link_libraries(pngfix PRIVATE png ZLIB::zlib ${M_LIBRARY})
  set(PNG_BIN_TARGETS pngfix)

  add_executable(png-fix-itxt ${png_fix_itxt_sources})
  target_link_libraries(png-fix-itxt PRIVATE ZLIB::zlib ${M_LIBRARY})
  list(APPEND PNG_BIN_TARGETS png-fix-itxt)
endif()

# Create source generation scripts.
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/scripts/cmake/genchk.cmake.in
               ${CMAKE_CURRENT_BINARY_DIR}/scripts/cmake/genchk.cmake
               @ONLY)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/scripts/cmake/genout.cmake.in
               ${CMAKE_CURRENT_BINARY_DIR}/scripts/cmake/genout.cmake
               @ONLY)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/scripts/cmake/gensrc.cmake.in
               ${CMAKE_CURRENT_BINARY_DIR}/scripts/cmake/gensrc.cmake
               @ONLY)

####
# Installation (https://github.com/forexample/package-example)

set(config_install_dir "lib/cmake/${PROJECT_NAME}")
set(include_install_dir "include")
set(generated_dir "${CMAKE_CURRENT_BINARY_DIR}/generated")

set(version_config "${generated_dir}/${PROJECT_NAME}ConfigVersion.cmake")
set(project_config "${generated_dir}/${PROJECT_NAME}Config.cmake")
set(targets_export_name "${PROJECT_NAME}Targets")
set(namespace "${PROJECT_NAME}::")

include(CMakePackageConfigHelpers)

# Note: PROJECT_VERSION is used as a VERSION
write_basic_package_version_file(
    "${version_config}" COMPATIBILITY SameMajorVersion
)

# Note: variable 'targets_export_name' used
configure_file("cmake/Config.cmake.in" "${project_config}" @ONLY)

install(
    TARGETS png
    EXPORT "${targets_export_name}"
    LIBRARY DESTINATION "lib"
    ARCHIVE DESTINATION "lib"
    RUNTIME DESTINATION "bin"
    INCLUDES DESTINATION "${include_install_dir}"
)

install(
    FILES ${libpng_public_hdrs}
    DESTINATION "${include_install_dir}"
)

install(
    EXPORT "${targets_export_name}"
    NAMESPACE "${namespace}"
    DESTINATION "${config_install_dir}"
)
