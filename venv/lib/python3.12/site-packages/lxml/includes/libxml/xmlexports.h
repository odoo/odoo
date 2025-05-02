/*
 * Summary: macros for marking symbols as exportable/importable.
 * Description: macros for marking symbols as exportable/importable.
 *
 * Copy: See Copyright for the status of this software.
 */

#ifndef __XML_EXPORTS_H__
#define __XML_EXPORTS_H__

/** DOC_DISABLE */
#if defined(_WIN32) || defined(__CYGWIN__)
  #ifdef LIBXML_STATIC
    #define XMLPUBLIC
  #elif defined(IN_LIBXML)
    #define XMLPUBLIC __declspec(dllexport)
  #else
    #define XMLPUBLIC __declspec(dllimport)
  #endif
#else /* not Windows */
  #define XMLPUBLIC
#endif /* platform switch */
/** DOC_ENABLE */

/*
 * XMLPUBFUN:
 *
 * Macro which declares an exportable function
 */
#define XMLPUBFUN XMLPUBLIC

/**
 * XMLPUBVAR:
 *
 * Macro which declares an exportable variable
 */
#define XMLPUBVAR XMLPUBLIC extern

/** DOC_DISABLE */
/* Compatibility */
#define XMLCALL
#define XMLCDECL
#if !defined(LIBXML_DLL_IMPORT)
#define LIBXML_DLL_IMPORT XMLPUBVAR
#endif
/** DOC_ENABLE */

#endif /* __XML_EXPORTS_H__ */


