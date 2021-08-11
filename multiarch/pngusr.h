#ifndef _PNG_USR_H_
#define _PNG_USR_H_

// This file is used to enable both the ARM and x86 archs to be built in the
// same project. This is necessary when building for macOS, iOS or tvOS when
// using a multiarch toolchain, but can also be used on other platforms.

#undef PNG_ARM_NEON_OPT
#undef PNG_INTEL_SSE_OPT
#undef PNG_MIPS_MSA_OPT
#undef PNG_POWERPC_VSX_OPT

// The ARM NEON flag gets autodetected in pngpriv.h so there's no need to set it.

#if defined(__i386__) || defined(__x86_64__)
#define PNG_INTEL_SSE_OPT 1
#endif

#if defined(__mips__)
#define PNG_MIPS_MSA_OPT 2
#endif

#if defined(__powerpc)
#define PNG_POWERPC_VSX_OPT 2
#endif

#endif
