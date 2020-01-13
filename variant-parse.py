#!/bin/env python3

import argparse
import sys
import os
from pyparsing import *
from pyparsing import pyparsing_common as ppc

typename_prefix = ""
funcname_prefix = ""

LBRACK, RBRACK, LBRACE, RBRACE, COLON, SEMI = map(Suppress, "[]{}:;")

ident = Word(alphas + "_", alphanums + "_").setName("identifier")

named_types = {}

def remove_prefix(text, prefix):
    return text[text.startswith(prefix) and len(prefix):]

output_file = None
def writeC(code, continued = False):
    if output_file:
        output_file.write(code)
        if not continued:
            output_file.write('\n')
    else:
        print(code, end='' if continued else '\n')

def genC(code, extra_vars = None):
    vars = {
        'tprefix': typename_prefix,
        'fprefix': funcname_prefix,
        'FPREFIX': funcname_prefix.upper()
    }
    if extra_vars:
        vars = {**vars, **extra_vars}
    return code.format_map(vars)
def escapeC(s):
    return s.replace('{', '{{').replace('}', '}}')

def C(code, extra_vars = None, continued = False):
    writeC(genC(code, extra_vars), continued)

def generate_header(filename):
    C(
"""/* generated code for {filename} */
#include <string.h>
#include <glib.h>

/********** Basic types and helpers *****************/

typedef struct {{
 gconstpointer base;
 gsize size;
}} {tprefix}Ref;

#define {FPREFIX}REF_READ_FRAME_OFFSET(_v, _index) {fprefix}ref_read_unaligned_le ((guchar*)((_v).base) + (_v).size - (offset_size * ((_index) + 1)), offset_size)
#define {FPREFIX}REF_ALIGN(_offset, _align_to) ((_offset + _align_to - 1) & ~(gsize)(_align_to - 1))

/* Note: clz is undefinded for 0, so never call this size == 0 */
G_GNUC_CONST static inline guint
{fprefix}ref_get_offset_size (gsize size)
{{
#if defined(__GNUC__) && (__GNUC__ >= 4) && defined(__OPTIMIZE__)
  /* Instead of using a lookup table we use nibbles in a lookup word */
  guint32 v = (guint32)0x88884421;
  return (v >> (((__builtin_clzl(size) ^ 63) / 8) * 4)) & 0xf;
#else
  if (size > G_MAXUINT16)
    {{
      if (size > G_MAXUINT32)
        return 8;
      else
        return 4;
    }}
  else
    {{
      if (size > G_MAXUINT8)
         return 2;
      else
         return 1;
    }}
#endif
}}

G_GNUC_PURE static inline gsize
{fprefix}ref_read_unaligned_le (guchar *bytes, guint   size)
{{
  union
  {{
    guchar bytes[GLIB_SIZEOF_SIZE_T];
    gsize integer;
  }} tmpvalue;

  tmpvalue.integer = 0;
  /* we unroll the size checks here so that memcpy gets constant args */
  if (size >= 4)
    {{
      if (size == 8)
        memcpy (&tmpvalue.bytes, bytes, 8);
      else
        memcpy (&tmpvalue.bytes, bytes, 4);
    }}
  else
    {{
      if (size == 2)
        memcpy (&tmpvalue.bytes, bytes, 2);
      else
        memcpy (&tmpvalue.bytes, bytes, 1);
    }}

  return GSIZE_FROM_LE (tmpvalue.integer);
}}

static inline void
__{fprefix}gstring_append_double (GString *string, double d)
{{
  gchar buffer[100];
  gint i;

  g_ascii_dtostr (buffer, sizeof buffer, d);
  for (i = 0; buffer[i]; i++)
    if (buffer[i] == '.' || buffer[i] == 'e' ||
        buffer[i] == 'n' || buffer[i] == 'N')
      break;

  /* if there is no '.' or 'e' in the float then add one */
  if (buffer[i] == '\\0')
    {{
      buffer[i++] = '.';
      buffer[i++] = '0';
      buffer[i++] = '\\0';
    }}
   g_string_append (string, buffer);
}}

static inline void
__{fprefix}gstring_append_string (GString *string, const char *str)
{{
  gunichar quote = strchr (str, '\\'') ? '"' : '\\'';

  g_string_append_c (string, quote);
  while (*str)
    {{
      gunichar c = g_utf8_get_char (str);

      if (c == quote || c == '\\\\')
        g_string_append_c (string, '\\\\');

      if (g_unichar_isprint (c))
        g_string_append_unichar (string, c);
      else
        {{
          g_string_append_c (string, '\\\\');
          if (c < 0x10000)
            switch (c)
              {{
              case '\\a':
                g_string_append_c (string, 'a');
                break;

              case '\\b':
                g_string_append_c (string, 'b');
                break;

              case '\\f':
                g_string_append_c (string, 'f');
                break;

              case '\\n':
                g_string_append_c (string, 'n');
                break;

              case '\\r':
                g_string_append_c (string, 'r');
                break;

              case '\\t':
                g_string_append_c (string, 't');
                break;

              case '\\v':
                g_string_append_c (string, 'v');
                break;

              default:
                g_string_append_printf (string, "u%04x", c);
                break;
              }}
           else
             g_string_append_printf (string, "U%08x", c);
        }}

      str = g_utf8_next_char (str);
    }}

  g_string_append_c (string, quote);
}}

/************** {tprefix}VariantRef *******************/

typedef {tprefix}Ref {tprefix}VariantRef;
static inline const GVariantType *
{tprefix}VariantRef_get_type ({tprefix}VariantRef v)
{{
  gsize size = v.size - 1;
  while (((guchar *)v.base)[size] != 0)
    size--;
  return (const GVariantType *)((guchar *)v.base + size + 1);
}}

static inline {tprefix}Ref
{tprefix}VariantRef_get_child ({tprefix}VariantRef v)
{{
  gsize size = v.size - 1;
  while (((guchar *)v.base)[size] != 0)
    size--;
  return ({tprefix}Ref) {{ v.base, size }};
}}

static inline GVariant *
{tprefix}VariantRef_dup_to_gvariant ({tprefix}VariantRef v)
{{
  return g_variant_new_from_data (G_VARIANT_TYPE_VARIANT, g_memdup (v.base, v.size), v.size, TRUE, g_free, NULL);
}}

static inline GVariant *
{tprefix}VariantRef_peek_as_gvariant ({tprefix}VariantRef v)
{{
  return g_variant_new_from_data (G_VARIANT_TYPE_VARIANT, v.base, v.size, TRUE, NULL, NULL);
}}

static inline GVariant *
{tprefix}VariantRef_dup_child_to_gvariant ({tprefix}VariantRef v)
{{
  const GVariantType  *type = {tprefix}VariantRef_get_type (v);
  {tprefix}Ref child = {tprefix}VariantRef_get_child (v);
  return g_variant_new_from_data (type, g_memdup (child.base, child.size), child.size, TRUE, g_free, NULL);
}}

static inline GVariant *
{tprefix}VariantRef_peek_child_as_gvariant ({tprefix}VariantRef v)
{{
  const GVariantType  *type = {tprefix}VariantRef_get_type (v);
  {tprefix}Ref child = {tprefix}VariantRef_get_child (v);
  return g_variant_new_from_data (type, child.base, child.size, TRUE, NULL, NULL);
}}

static inline GString *
{tprefix}VariantRef_format ({tprefix}VariantRef v, GString *s, gboolean type_annotate)
{{
#ifdef SHALLOW_VARIANT_FORMAT
  const GVariantType  *type = {tprefix}VariantRef_get_type (v);
  g_string_append_printf (s, "<@%.*s>", (int)g_variant_type_get_string_length (type), (const char *)type);
  return s;
#else
  GVariant *gv = {tprefix}VariantRef_peek_as_gvariant (v);
  return g_variant_print_string (gv, s, TRUE);
#endif
}}

static inline char *
{tprefix}VariantRef_print ({tprefix}VariantRef v, gboolean type_annotate)
{{
  GString *s = g_string_new ("");
  {tprefix}VariantRef_format (v, s, type_annotate);
  return g_string_free (s, FALSE);
}}""", {'filename': filename})

def generate_footer(filename):
    C('', {'filename': filename})

def align_down(value, alignment):
    return value & ~(alignment - 1)

def align_up(value, alignment):
    return align_down(value + alignment - 1, alignment)

def add_named_type(name, type):
    assert not name in named_types
    type.set_typename(name, True)
    named_types[name] = type

def get_named_type(name):
    name = typename_prefix + name
    assert name in named_types
    return named_types[name]

class TypeDef:
    def __init__(self, name, type):
        name = typename_prefix + name
        self.name = name
        self.type = type

        add_named_type(name, type)

    def generate(self, generated):
        def do_generate (type, generated):
            for c in type.get_children():
                do_generate (c, generated)
            if type.typename != None and type.typename not in generated:
                generated[type.typename] = True
                type.generate()

        do_generate(self.type, generated)


class Type:
    def __init__(self):
        self.typename = None

    def typestring(self):
        assert False

    def set_typename(self, name, override = False):
        if self.typename == None or override:
            self.typename = name
            self.propagate_typename(name)

    def propagate_typename(self, typename):
        pass

    def is_basic(self):
        return False

    def is_fixed(self):
        return False

    def get_fixed_size(self):
         return None

    def alignment(self):
        return 1

    def get_children(self):
        return []

    def add_expansion_vars(self, vars):
        pass

    def genC(self, code, extra_vars = None):
        vars = {
            'typename': self.typename,
            'typestring': self.typestring(),
            'ctype': self.get_ctype(),
            'alignment': self.alignment(),
            'fixed_size': self.get_fixed_size()
        }
        if extra_vars:
            vars = {**vars, **extra_vars}
        self.add_expansion_vars(vars)
        return genC(code, vars)

    def C(self, code, extra_vars = None, continued=False):
        writeC(self.genC(code, extra_vars), continued)

    def generate(self):
        self.C (
'''
/************** {typename} *******************/

typedef {tprefix}Ref {typename}Ref;
#define {typename}_typestring "{typestring}"
#define {typename}_typeformat G_VARIANT_TYPE ({typename}_typestring)

static inline {typename}Ref
{typename}Ref_from_variant (GVariant *v)
{{
    g_assert (g_variant_type_equal (g_variant_get_type (v), {typename}_typestring));
    return ({typename}Ref) {{ g_variant_get_data (v), g_variant_get_size (v) }};
}}

static inline GVariant *
{typename}Ref_dup_to_variant ({typename}Ref v)
{{
  return g_variant_new_from_data ({typename}_typeformat, g_memdup (v.base, v.size), v.size, TRUE, g_free, NULL);
}}

static inline {typename}Ref
{typename}Ref_from_variant_ref ({tprefix}VariantRef v) {{
    g_assert (g_variant_type_equal({tprefix}VariantRef_get_type (v), {typename}_typestring));
    return ({typename}Ref) {tprefix}VariantRef_get_child (v);
}}
''')

    def generate_print(self):
        self.C (
'''
static inline char *
{typename}Ref_print ({typename}Ref v, gboolean type_annotate)
{{
  GString *s = g_string_new ("");
  {typename}Ref_format (v, s, type_annotate);
  return g_string_free (s, FALSE);
}}
''')

    def get_ctype(self):
         return self.typename + "Ref"

    def can_printf_format(self):
         return False

    def generate_append_value(self, value, with_type_annotate):
        return self.genC("{typename}Ref_format ({value}, s, {type_annotate});", {'value': value, 'type_annotate': with_type_annotate})

basic_types = {
    "boolean": ("b", True, 1, "gboolean", "", '%s'),
    "byte": ("y", True, 1, "guint8", "byte ", '0x%02x'),
    "int16": ("n", True, 2, "gint16", "int16 ", '%"G_GINT16_FORMAT"'),
    "uint16": ("q", True, 2, "guint16", "uint16 ", '%"G_GUINT16_FORMAT"'),
    "int32": ("i", True, 4, "gint32", "", '%"G_GINT32_FORMAT"'),
    "uint32": ("u", True, 4, "guint32", "uint32 ", '%"G_GUINT32_FORMAT"'),
    "int64": ("x", True, 8, "gint64", "int64 ", '%"G_GINT64_FORMAT"'),
    "uint64": ("t", True, 8, "guint64", "uint64 ", '%"G_GUINT64_FORMAT"'),
    "handle": ("h", True, 4, "guint32", "handle ", '%"G_GINT32_FORMAT"'),
    "double": ("d", True, 8, "double", "", None), # double formating is special
    "string": ("s", False, 1, "const char *", "", None), # String formating is special
    "objectpath": ("o", False, 1, "const char *", "objectpath ", "\\'%s\\'"),
    "signature": ("g", False, 1, "const char *", "signature ", "\\'%s\\'"),
}

class BasicType(Type):
    def __init__(self, kind):
        super().__init__()
        assert kind in basic_types
        self.kind = kind
    def __repr__(self):
         return "BasicType(%s)" % self.kind
    def typestring(self):
         return basic_types[self.kind][0]
    def set_typename(self, name):
        pass # No names for basic types
    def is_basic(self):
        return True
    def is_fixed(self):
         return basic_types[self.kind][1]
    def get_fixed_size(self):
         return basic_types[self.kind][2]
    def alignment(self):
         return basic_types[self.kind][2]
    def get_ctype(self):
         return basic_types[self.kind][3]
    def get_read_ctype(self):
        if self.kind == "boolean":
            return "guint8"
        return self.get_ctype()
    def get_type_annotation(self):
        return basic_types[self.kind][4]
    def get_format_string(self):
        return basic_types[self.kind][5]
    def convert_value_for_format(self, value):
        if self.kind == "boolean":
            value = '(%s) ? "true" : "false"' % value
        return value
    def can_printf_format(self):
         return self.get_format_string() != None
    def add_expansion_vars(self, vars):
        vars['readctype'] = self.get_read_ctype()
    def generate_append_value(self, value, with_type_annotate):
        # Special case some basic types
        genC = self.genC
        if self.kind == "string":
            return genC('__{fprefix}gstring_append_string (s, {value});', {'value': value})
        elif self.kind == "double":
            return genC ('__{fprefix}gstring_append_double (s, {value});', {'value': value})
        else:
            value = self.convert_value_for_format(value)
            if with_type_annotate != "FALSE" and self.get_type_annotation() != "":
                return genC('g_string_append_printf (s, "%s{format}", {type_annotate} ? "{annotate}" : "", {value});',
                  {
                      'format': self.get_format_string(),
                      'type_annotate': with_type_annotate,
                      'annotate': self.get_type_annotation(),
                      'value': value
                  })
            else:
                return genC('g_string_append_printf (s, "{format}", {value});',
                  {
                      'format': self.get_format_string(),
                      'value': value
                  }
                )
    def equal_code(self, val1, val2):
        if self.is_fixed():
            return "%s == %s" % (val1, val2)
        else: # String type
            return "strcmp(%s, %s) == 0" % (val1, val2)
    def canonicalize_code(self, val):
        if self.kind == "boolean":
            return "!!%s" % val
        return val

class ArrayType(Type):
    def __init__(self, element_type):
        super().__init__()
        self.element_type = element_type

        if element_type.is_basic():
            self.typename = typename_prefix + "Arrayof" + self.element_type.kind
        elif element_type.typename:
            self.typename = typename_prefix + "Arrayof" + remove_prefix(element_type.typename, typename_prefix)

    def __repr__(self):
         return "ArrayType<%s>(%s)" % (self.typename, repr(self.element_type))
    def typestring(self):
         return "a" + self.element_type.typestring()
    def propagate_typename(self, name):
        self.element_type.set_typename (name + "Element")
    def alignment(self):
        return self.element_type.alignment()
    def get_children(self):
        return [self.element_type]
    def add_expansion_vars(self, vars):
        vars['element_ctype'] = self.element_type.get_ctype()
        vars['element_typename'] = self.element_type.typename
        vars['element_fixed_size'] = self.element_type.get_fixed_size()
        vars['element_alignment'] = self.element_type.alignment()
        if self.element_type.is_basic():
            vars['element_read_ctype'] = self.element_type.get_read_ctype()

    def generate(self):
        super().generate()
        C = self.C
        C("static inline gsize")
        C("{typename}Ref_get_length({typename}Ref v)")
        C("{{")
        if self.element_type.is_fixed():
            C("  return v.size / {element_fixed_size};")
        else:
            C("  guint offset_size = {fprefix}ref_get_offset_size (v.size);");
            C("  gsize last_end = {FPREFIX}REF_READ_FRAME_OFFSET(v, 0);");
            C("  return (v.size - last_end) / offset_size;")
        C("}}")
        C("static inline {element_ctype}")
        C("{typename}Ref_get_at({typename}Ref v, gsize index)")
        C("{{")
        if self.element_type.is_fixed():
            if self.element_type.is_basic():
                C("  return ({element_ctype})G_STRUCT_MEMBER({element_read_ctype}, v.base, index * {element_fixed_size});")
            else:
                C("  return ({element_typename}Ref) {{ G_STRUCT_MEMBER_P(v.base, index * {element_fixed_size}), {element_fixed_size}}};")
        else:
            # non-fixed size
            C("  guint offset_size = {fprefix}ref_get_offset_size (v.size);")
            C("  gsize last_end = {FPREFIX}REF_READ_FRAME_OFFSET(v, 0);");
            C("  gsize len = (v.size - last_end) / offset_size;")
            C("  gsize start = 0;")
            if not self.element_type.is_basic():
                C("  gsize end = {FPREFIX}REF_READ_FRAME_OFFSET(v, len - index - 1);");
            C("  if (index > 0) {{")
            C("    start = {FPREFIX}REF_READ_FRAME_OFFSET(v, len - index);")
            C("    start = {FPREFIX}REF_ALIGN(start, {element_alignment});")
            C("  }}");
            if self.element_type.is_basic(): # non-fixed basic == Stringlike
                C("  return ((const char *)v.base) + start;")
            else:
                C("  return ({element_typename}Ref) {{ ((const char *)v.base) + start, end - start }};")
        C("}}")

        C(
"""static inline GString *
{typename}Ref_format ({typename}Ref v, GString *s, gboolean type_annotate)
{{
  gsize len = {typename}Ref_get_length(v);
  gsize i;
  if (len == 0 && type_annotate)
    g_string_append_printf (s, \"@%s \", {typename}_typestring);
  g_string_append_c (s, '[');
  for (i = 0; i < len; i++) {{
    if (i != 0)
      g_string_append (s, \", \");
    {append_element_code}
  }}
  g_string_append_c (s, ']');
  return s;
}}""",  {
    'append_element_code': escapeC(self.element_type.generate_append_value(self.genC("{typename}Ref_get_at(v, i)"), "((i == 0) ? type_annotate : FALSE)"))
})

        self.generate_print()

class DictType(Type):
    def __init__(self, key_type, value_type):
        super().__init__()
        self.key_type = key_type
        self.value_type = value_type

        self._fixed_element = value_type.is_fixed() and key_type.is_fixed();
        if self._fixed_element:
            fixed_pos = key_type.get_fixed_size()
            fixed_pos = align_up(fixed_pos, value_type.alignment()) + value_type.get_fixed_size()
            self._fixed_element_size = align_up(fixed_pos, self.alignment())
        else:
            self._fixed_element_size = None

    def __repr__(self):
         return "DictType<%s>(%s, %s)" % (self.typename, repr(self.key_type), repr(self.value_type))
    def typestring(self):
         return "a{%s%s}" % (self.key_type.typestring(), self.value_type.typestring())
    def propagate_typename(self, name):
        self.value_type.set_typename (name + "Value")
    def alignment(self):
        return max(self.value_type.alignment(), self.key_type.alignment())
    def element_is_fixed(self):
        return self._fixed_element
    def element_fixed_size(self):
        return self._fixed_element_size
    def get_children(self):
        return [self.key_type, self.value_type]
    def add_expansion_vars(self, vars):
        vars['element_fixed_size'] = self.element_fixed_size()
        vars['value_ctype'] = self.value_type.get_ctype()
        vars['value_typename'] = self.value_type.typename
        vars['value_fixed_size'] = self.value_type.get_fixed_size()
        vars['value_alignment'] = self.value_type.alignment()
        if self.value_type.is_basic():
            vars['value_read_ctype'] = self.value_type.get_read_ctype()
        vars['key_ctype'] = self.key_type.get_ctype()
        if self.key_type.is_basic():
            vars['key_read_ctype'] = self.key_type.get_read_ctype()

    def generate(self):
        C=self.C
        super().generate()
        C('typedef {tprefix}Ref {typename}EntryRef;')
        C('')

        C("static inline gsize")
        C("{typename}Ref_get_length ({typename}Ref v)")
        C("{{")
        if self.element_is_fixed():
            C("  return v.size / {element_fixed_size};")
        else:
            C("  guint offset_size = {fprefix}ref_get_offset_size (v.size);");
            C("  gsize last_end = {FPREFIX}REF_READ_FRAME_OFFSET(v, 0);");
            C("  return (v.size - last_end) / offset_size;")
        C("}}")

        C('')

        C("static inline {typename}EntryRef")
        C("{typename}Ref_get_at ({typename}Ref v, gsize index)")
        C("{{")
        if self.element_is_fixed():
            C("  return ({typename}EntryRef) {{ G_STRUCT_MEMBER_P(v.base, index * {element_fixed_size}), {element_fixed_size} }};")
        else:
            # non-fixed size
            C("  guint offset_size = {fprefix}ref_get_offset_size (v.size);")
            C("  gsize last_end = {FPREFIX}REF_READ_FRAME_OFFSET(v, 0);");
            C("  gsize len = (v.size - last_end) / offset_size;")
            C("  gsize start = 0;")
            C("  gsize end = {FPREFIX}REF_READ_FRAME_OFFSET(v, len - index - 1);");
            C("  if (index > 0) {{")
            C("    start = {FPREFIX}REF_READ_FRAME_OFFSET(v, len - index);")
            C("    start = {FPREFIX}REF_ALIGN(start, {alignment});")
            C("  }}");
            C("  return ({typename}EntryRef) {{ ((const char *)v.base) + start, end - start }};")
        C("}}")

        C('')

        C("static inline {key_ctype}")
        C("{typename}EntryRef_get_key ({typename}EntryRef v)")
        C("{{")
        # Keys are always basic
        if self.key_type.is_fixed():
            C("  return ({key_ctype})*(({key_read_ctype} *)v.base);")
        else: # string-style
            C("  return ({key_ctype})v.base;")
        C("}}")

        C('')

        C("static inline {value_ctype}")
        C("{typename}EntryRef_get_value ({typename}EntryRef v)")
        C("{{")
        if not self.key_type.is_fixed():
            C("  guint offset_size = {fprefix}ref_get_offset_size (v.size);")
            C("  gsize end = {FPREFIX}REF_READ_FRAME_OFFSET(v, 0);");
            C("  gsize offset = {FPREFIX}REF_ALIGN(end, {value_alignment});")
            offset = "offset"
            end = "(v.size - offset_size)"
        else:
            # Fixed key, so known offset
            offset = align_up(self.key_type.get_fixed_size(), self.value_type.alignment())
            end = "v.size"

        if self.value_type.is_basic():
            if self.value_type.is_fixed():
                C("  return ({value_ctype})*(({value_read_ctype} *)((char *)v.base + {offset}));", {'offset': offset})
            else: # string-style
                C("  return ({value_ctype})v.base + {offset};", {'offset': offset})
        else:
            C("  return ({value_typename}Ref) {{ (char *)v.base + {offset}, {end} - {offset} }};", {'offset': offset, 'end': end })

        C("}}")

        C('')

        C(
"""static inline gboolean
{typename}Ref_lookup({typename}Ref v, {key_ctype} key, {value_ctype} *out)
{{
  gsize len = {typename}Ref_get_length(v);
  {key_ctype} canonical_key = {canonicalize};
  gsize i;

  for (i = 0; i < len; i++)
    {{
        {typename}EntryRef e = {typename}Ref_get_at(v, i);
        {key_ctype} e_key = {typename}EntryRef_get_key(e);
        if ({equal})
          {{
             *out = {typename}EntryRef_get_value (e);
             return TRUE;
          }}
    }}
    return FALSE;
}}""",
            {
                'equal': self.key_type.equal_code("canonical_key", "e_key"),
                'canonicalize': self.key_type.canonicalize_code("key")
            })

        C('')

        C(
"""static inline GString *
{typename}Ref_format ({typename}Ref v, GString *s, gboolean type_annotate)
{{
  gsize len = {typename}Ref_get_length(v);
  gsize i;

  if (len == 0 && type_annotate)
    g_string_append_printf (s, \"@%s \", {typename}_typestring);

  g_string_append_c (s, '{{');
  for (i = 0; i < len; i++) {{
    {typename}EntryRef entry = {typename}Ref_get_at(v, i);
    if (i != 0)
      g_string_append (s, \", \");
    {append_key_code}
    g_string_append (s, ": ");
    {append_value_code}
  }}
  g_string_append_c (s, '}}');
  return s;
}}""",{
    'append_key_code': escapeC(self.key_type.generate_append_value(self.genC("{typename}EntryRef_get_key(entry)"), "type_annotate")),
    'append_value_code': escapeC(self.value_type.generate_append_value(self.genC("{typename}EntryRef_get_value(entry)"), "type_annotate")),
})

        self.generate_print()

class MaybeType(Type):
    def __init__(self, element_type):
        super().__init__()
        self.element_type = element_type
        if element_type.is_basic():
            self.typename = typename_prefix + "Maybe" + self.element_type.kind
        elif element_type.typename:
            self.typename = typename_prefix + "Maybe" + remove_prefix(element_type.typename, typename_prefix)
    def __repr__(self):
         return "MaybeType<%s>(%s, %s)" % (self.typename, repr(self.element_type))
    def typestring(self):
         return "m" + self.element_type.typestring()
    def propagate_typename(self, name):
        self.element_type.set_typename (name + "Element")
    def alignment(self):
        return self.element_type.alignment()
    def get_children(self):
        return [self.element_type]
    def add_expansion_vars(self, vars):
        vars['element_ctype'] = self.element_type.get_ctype()
        vars['element_typename'] = self.element_type.typename
        vars['element_fixed_size'] = self.element_type.get_fixed_size()
        vars['element_alignment'] = self.element_type.alignment()
        if self.element_type.is_basic():
            vars['element_read_ctype'] = self.element_type.get_read_ctype()

    def generate(self):
        super().generate()

        C=self.C
        # has_value
        C(
"""static inline gboolean
{typename}Ref_has_value({typename}Ref v)
{{
  return v.size != 0;
}}""")

        # Getter
        C("static inline {element_ctype}")
        C("{typename}Ref_get_value({typename}Ref v)")
        C("{{")
        C("  g_assert(v.size != 0);")

        if self.element_type.is_basic():
            if self.element_type.is_fixed():
                C("  return ({element_ctype})*(({element_read_ctype} *)v.base);")
            else: # string
                C("  return ({element_ctype})v.base;")
        else:
            if self.element_type.is_fixed():
                # Fixed means use whole size
                size = "v.size"
            else:
                # Otherwise, ignore extra zero byte
                size = "(v.size - 1)"
            C("  return ({element_typename}Ref) {{ v.base, {size} }};", { 'size': size })
        C("}}")

        C("static inline GString *")
        C("{typename}Ref_format ({typename}Ref v, GString *s, gboolean type_annotate)")
        C("{{")
        C("  if (type_annotate)")
        C('    g_string_append_printf (s, "@%s ", {typename}_typestring);')
        C("  if (v.size != 0)")
        C("    {{")
        if isinstance(self.element_type, MaybeType):
            C('      g_string_append (s, "just ");')
        C('      {append_element_code}', {
            'append_element_code': escapeC(self.element_type.generate_append_value(self.genC("{typename}Ref_get_value(v)"), "FALSE"))
        })
        C("    }}")
        C("  else")
        C("    {{")
        C('      g_string_append (s, "nothing");')
        C("    }}")
        C("  return s;")
        C("}}")
        self.generate_print()

class VariantType(Type):
    def __init__(self):
        super().__init__()
        self.typename = typename_prefix + "Variant"
    def __repr__(self):
         return "VariantType()"
    def typestring(self):
         return "v"
    def set_typename(self, name):
        pass # No names for variant
    def alignment(self):
        return 8
    def generate(self):
        pass # These are hardcoded in the prefix so all types can use it

class Field:
    def __init__(self, name, attributes, type):
        self.name = name
        self.attributes = attributes
        self.type = type
        self.last = False
        self.struct = None
        self.index = None

    def __repr__(self):
         return "Field(%s, %s)" % (self.name, self.type)

    def propagate_typename(self, struct_name):
        self.type.set_typename (struct_name + "_" + self.name)

    def genC(self, code, extra_vars = None):
        vars = {
            'fieldname': self.name,
            'structname': self.struct.typename,
            'fieldindex': self.fieldindex,
        }
        if extra_vars:
            vars = {**vars, **extra_vars}
        return self.type.genC(code, vars)

    def C(self, code, extra_vars = None, continued = False):
        writeC(self.genC(code, extra_vars), continued=continued)

    def generate(self):
        # Getter
        C=self.C
        C("#define {structname}_indexof_{fieldname} {fieldindex}")
        C("static inline {ctype}")
        C("{structname}Ref_get_{fieldname}({structname}Ref v)")
        C("{{")
        has_offset_size = False
        if self.table_i == -1:
            offset = "((%d) & (~(gsize)%d)) + %d" % (self.table_a + self.table_b, self.table_b, self.table_c)
        else:
            has_offset_size = True
            C("  guint offset_size = {fprefix}ref_get_offset_size (v.size);");
            C("  gsize last_end = {FPREFIX}REF_READ_FRAME_OFFSET(v, {table_i});", {'table_i': self.table_i });
            offset = "((last_end + %d) & (~(gsize)%d)) + %d" % (self.table_a + self.table_b, self.table_b, self.table_c)

        if self.type.is_basic():
            if self.type.is_fixed():
                C("  return ({ctype})G_STRUCT_MEMBER({readctype}, v.base, {offset});", {'offset': offset})
            else: # string
                C("  return &G_STRUCT_MEMBER(char, v.base, {offset});", {'offset': offset})
        else:
            if self.type.is_fixed():
                C("  return ({typename}Ref) {{ G_STRUCT_MEMBER_P(v.base, {offset}), {fixed_size} }};", {'offset': offset})
            else:
                if not has_offset_size:
                    has_offset_size = True
                    C("  guint offset_size = {fprefix}ref_get_offset_size (v.size);");
                C("  gsize start = {offset};", {'offset': offset});
                if self.last:
                    C("  gsize end = v.size - offset_size * {framing_offset_size};", {'framing_offset_size': self.struct.framing_offset_size })
                else:
                    C("  gsize end = {FPREFIX}REF_READ_FRAME_OFFSET(v, %d);" % (self.table_i + 1));
                C("  return ({typename}Ref) {{ G_STRUCT_MEMBER_P(v.base, start), end - start }};")
        C("}}")

class StructType(Type):
    def __init__(self, fields):
        super().__init__()
        self.fields = list(fields)

        if len(self.fields) > 0:
            self.fields[len(self.fields) - 1].last = True

        for i, f in enumerate(self.fields):
            f.struct = self
            f.fieldindex = i

        framing_offset_size = 0
        fixed = True
        fixed_pos = 0
        for f in fields:
            if f.type.is_fixed():
                fixed_pos = align_up(fixed_pos, f.type.alignment()) + f.type.get_fixed_size()
            else:
                fixed = False
                if not f.last:
                    framing_offset_size = framing_offset_size + 1

        self.framing_offset_size = framing_offset_size
        self._fixed = fixed
        self._fixed_size = None;
        if fixed:
            if fixed_pos == 0: # Special case unit struct
                self._fixed_size = 1;
            else:
                # Round up to alignment
                self._fixed_size = align_up(fixed_pos, self.alignment())

        def tuple_align(offset, alignment):
            return offset + ((-offset) & alignment)

        # This is code equivalend to tuple_generate_table() in gvariantinfo.c, see its docs
        i = -1
        a = 0
        b = 0
        c = 0
        for f in fields:
            d = f.type.alignment() - 1;
            e = f.type.get_fixed_size() if f.type.is_fixed() else 0

            # align to 'd'
            if d <= b: # rule 1
                c = tuple_align(c, d)
            else: # rule 2
                a = a + tuple_align(c, b)
                b = d
                c = 0

            # the start of the item is at this point (ie: right after we
            # have aligned for it).  store this information in the table.
            f.table_i = i
            f.table_a = a
            f.table_b = b
            f.table_c = c

            # "move past" the item by adding in its size.
            if e == 0:
                # variable size:
                #
                # we'll have an offset stored to mark the end of this item, so
                # just bump the offset index to give us a new starting point
                # and reset all the counters.
                i = i + 1
                a = b = c = 0
            else:
                # fixed size
                c = c + e # rule 3

    def __repr__(self):
        return "StructType<%s>(%s)" % (self.typename, ",".join(map(repr, self.fields)))

    def typestring(self):
        res = ['(']
        for f in self.fields:
            res.append(f.type.typestring())
        res.append(')')
        return "".join(res)

    def get_children(self):
        children = []
        for f in self.fields:
            children.append(f.type)
        return children

    def propagate_typename(self, name):
        for f in self.fields:
            f.propagate_typename(name)

    def alignment(self):
        alignment = 1;
        for f in self.fields:
            alignment = max(alignment, f.type.alignment())
        return alignment

    def is_fixed(self):
        return self._fixed;
    def get_fixed_size(self):
        return self._fixed_size

    def generate(self):
        super().generate()
        for i, f in enumerate(self.fields):
            f.generate()
        C=self.C
        C("static inline GString *")
        C("{typename}Ref_format ({typename}Ref v, GString *s, gboolean type_annotate)")
        C("{{")

        # Create runs of things we can combine into single printf
        field_runs = []
        current_run = None
        for f in self.fields:
            if current_run and f.type.can_printf_format() == current_run[0].type.can_printf_format():
                current_run.append(f)
            else:
                current_run = [f]
                field_runs.append(current_run)

        for i, run in enumerate(field_runs):
            if run[0].type.can_printf_format():
                # A run of printf fields
                C('  g_string_append_printf (s, "%s' % ("(" if i == 0 else ""), continued=True)
                for f in run:
                    if f.type.get_type_annotation() != "":
                        C('%s', continued=True)
                    C('%s' % (f.type.get_format_string()), continued=True)
                    if not f.last:
                        C(', ', continued=True)
                    elif len(self.fields) == 1:
                        C(',)', continued=True)
                    else:
                        C(')', continued=True)
                C('",')
                for j, f in enumerate(run):
                    if f.type.get_type_annotation() != "":
                        C('                   type_annotate ? "%s" : "",' % (f.type.get_type_annotation()))
                    value = f.type.convert_value_for_format("{structname}Ref_get_{fieldname}(v)".format(structname=self.typename, fieldname=f.name))
                    C('                   %s%s' % (value, "," if j != len(run) - 1 else ");"))
            else:
                # A run of container fields
                if i == 0:
                    C('  g_string_append (s, "(");')
                for f in run:
                    C('  {append_field_code}', {'append_field_code': escapeC(f.type.generate_append_value(f.genC("{structname}Ref_get_{fieldname}(v)"), "type_annotate"))})
                    if not f.last:
                        C('  g_string_append (s, ", ");')
                    elif len(self.fields) == 1:
                        C('  g_string_append (s, ",)");')
                    else:
                        C('  g_string_append (s, ")");')
        C("  return s;")
        C("}}")
        self.generate_print()

typeSpec = Forward()

basicType = oneOf(basic_types.keys()).setParseAction(lambda toks: BasicType(toks[0]))

variantType = Keyword("variant").setParseAction(lambda toks: VariantType())

arrayType = (LBRACK + RBRACK + typeSpec).setParseAction(lambda toks: ArrayType(toks[0]))

dictType = (LBRACK + basicType + RBRACK + typeSpec).setParseAction(lambda toks: DictType(toks[0], toks[1]))

maybeType = (Suppress("?") + typeSpec).setParseAction(lambda toks: MaybeType(toks[0]))

fieldAttribute = oneOf("bigendian littleendian nativeendian")

field = (ident + COLON + Group(ZeroOrMore(fieldAttribute)) + typeSpec + SEMI).setParseAction(lambda toks: Field(toks[0], toks[1], toks[2]))

structType = (LBRACE + ZeroOrMore(field) + RBRACE).setParseAction(lambda toks: StructType(toks))

namedType = ident.copy().setParseAction(lambda toks: get_named_type(str(toks[0])))

def handleNameableType(toks):
    type = toks[-1]
    if len(toks) == 2:
        name = toks[0]
        add_named_type(typename_prefix + name, type)
    return type

nameableType = (Optional((Suppress("'") + ident).leaveWhitespace()) + (arrayType ^ maybeType ^ dictType ^ structType)).setParseAction(handleNameableType)

typeSpec <<= basicType  ^ variantType ^ namedType ^ nameableType

typeDef = (Suppress(Keyword("type")) + ident + typeSpec + SEMI).setParseAction(lambda toks: TypeDef(toks[0], toks[1]))

typeDefs = ZeroOrMore(typeDef).ignore(cppStyleComment)

def generate(typedefs, filename):
    generate_header(filename)
    generated = {}
    for td in typedefs:
        td.generate(generated)
    generate_footer(filename)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate variant accessors.')
    parser.add_argument('--prefix', help='prefix')
    parser.add_argument('--outfile', help='output filename')
    parser.add_argument('file')
    args = parser.parse_args()
    if args.prefix:
        typename_prefix = args.prefix[0].upper() + args.prefix[1:]
        funcname_prefix = args.prefix + "_"
    if args.outfile:
        output_file = open(args.outfile, "w")

    with open(args.file, "r") as f:
        testdata = f.read()
        try:
            typedefs = typeDefs.parseString(testdata, parseAll=True)
            generate(typedefs, os.path.basename(args.file))
        except ParseException as pe:
            print("Parse error:", pe)
            sys.exit(1)
