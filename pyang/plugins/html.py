"""Html output plugin

Idea copied from libsmi.
"""

import optparse
import sys
import re

from pyang import plugin
from pyang import statements

def pyang_plugin_init():
    plugin.register_plugin(HtmlPlugin())

class HtmlPlugin(plugin.PyangPlugin):
    def add_output_format(self, fmts):
        self.multiple_modules = True
        fmts['html'] = self

    def add_opts(self, optparser):
        optlist = [
            optparse.make_option("--html-depth",
                                 type="int",
                                 dest="html_depth",
                                 help="Number of levels to print"),
            optparse.make_option("--html-path",
                                 dest="html_path",
                                 help="Subtree to print"),
            optparse.make_option("--html-print-groupings",
                                 dest="html_print_groupings",
                                 action="store_true",
                                 help="Print groupings"),
            ]
        g = optparser.add_option_group("HTML output specific options")
        g.add_options(optlist)

    def setup_ctx(self, ctx):
        pass

    def setup_fmt(self, ctx):
        # XXX should check what this does
        ctx.implicit_errors = False

    def emit(self, ctx, modules, fd):
        if ctx.opts.html_path is not None:
            path = ctx.opts.html_path.split('/')
            if path[0] == '':
                path = path[1:]
        else:
            path = None
        emit_html(ctx, modules, fd, ctx.opts.html_depth, path)

def emit_html(ctx, modules, fd, depth, path):
    emit_header(ctx, fd)
    emit_toc(ctx, modules, fd, depth, path)
    for module in modules:
        emit_module(ctx, module, fd, depth, path)
    emit_footer(ctx, fd)

def emit_header(ctx, fd):
    fd.write('''STANDARD FIRST LINE
<html>
  <head>
  </head>

  <body>
''')

def emit_toc(ctx, modules, fd, depth, path):
    fd.write('''
    <toc/>

''')

def emit_footer(ctx, fd):
    fd.write('''
  </body>
</html>
''')
        
def emit_module(ctx, module, fd, depth, path):
    printed_header = False

    # XXX printed_header logic is wrong for multiple modules
    def print_header():
        bstr = ""
        b = module.search_one('belongs-to')
        if b is not None:
            bstr = " (belongs-to %s)" % b.arg
        #fd.write("%s: %s%s\n" % (module.keyword, module.arg, bstr))
        fd.write("    <h1>%s %s</h1>\n" %
                 (module.keyword.capitalize(), module.arg))
        printed_header = True

    # XXX not included in tree output
    fd.write("    <h2>Imports</h2>\n")
    for i in module.search('import'):
        mod = ctx.get_module(i.arg)
        fd.write("    %s\n" % mod.arg)

    chs = [ch for ch in module.i_children
           if ch.keyword in statements.data_definition_keywords]
    if path is not None and len(path) > 0:
        chs = [ch for ch in chs if ch.arg == path[0]]
        path = path[1:]

    if len(chs) > 0:
        if not printed_header:
            print_header()
            printed_header = True
        fd.write("    <!-- children -->\n")
        fd.write("    <table>\n")
        fd.write("      <th>\n")
        fd.write("        <td>Name</td>\n")
        fd.write("      </th>\n")
        print_children(chs, module, fd, '       ', path, 'data', depth)
        fd.write("    </table>\n")

    mods = [module]
    for i in module.search('include'):
        subm = ctx.get_module(i.arg)
        if subm is not None:
            mods.append(subm)
    for m in mods:
        for augment in m.search('augment'):
            if (hasattr(augment.i_target_node, 'i_module') and
                augment.i_target_node.i_module not in modules + mods):
                # this augment has not been printed; print it
                if not printed_header:
                    print_header()
                    printed_header = True
                fd.write("#### augment %s:\n" % augment.arg)
                #print_children(augment.i_children, m, fd,
                #               ' ', path, 'augment', depth)

    rpcs = [ch for ch in module.i_children
            if ch.keyword == 'rpc']
    if path is not None:
        if len(path) > 0:
            rpcs = [rpc for rpc in rpcs if rpc.arg == path[0]]
            path = path[1:]
        else:
            rpcs = []
    if len(rpcs) > 0:
        if not printed_header:
            print_header()
            printed_header = True
        pass #fd.write("rpcs:\n")
        fd.write("    <!-- rpcs -->\n")
        print_children(rpcs, module, fd, ' ', path, 'rpc', depth)

    notifs = [ch for ch in module.i_children
              if ch.keyword == 'notification']
    if path is not None:
        if len(path) > 0:
            notifs = [n for n in notifs if n.arg == path[0]]
            path = path[1:]
        else:
            notifs = []
    if len(notifs) > 0:
        if not printed_header:
            print_header()
            printed_header = True
        pass #fd.write("notifications:\n")
        fd.write("    <!-- notifications -->\n")
        print_children(notifs, module, fd, ' ', path, 'notification', depth)

    if ctx.opts.html_print_groupings and len(module.i_groupings) > 0:
        if not printed_header:
            print_header()
            printed_header = True
        pass #fd.write("groupings:\n")
        for gname in module.i_groupings:
            pass #fd.write('  ' + gname + '\n')
            g = module.i_groupings[gname]
            print_children(g.i_children, module, fd, '   ', path,
                           'grouping', depth)
            pass #fd.write('\n')

def print_children(i_children, module, fd, prefix, path, mode, depth, width=0):
    if depth == 0:
        #if i_children: fd.write(prefix + '     ...\n')
        return
    def get_width(w, chs):
        for ch in chs:
            if ch.keyword in ['choice', 'case']:
                w = get_width(w, ch.i_children)
            else:
                if ch.i_module.i_modulename == module.i_modulename:
                    nlen = len(ch.arg)
                else:
                    nlen = len(ch.i_module.i_prefix) + 1 + len(ch.arg)
                if nlen > w:
                    w = nlen
        return w

    if width == 0:
        width = get_width(0, i_children)

    for ch in i_children:
        if ((ch.keyword == 'input' or ch.keyword == 'output') and
            len(ch.i_children) == 0):
            pass
        else:
            newprefix = prefix
            if ch.keyword == 'input':
                mode = 'input'
            elif ch.keyword == 'output':
                mode = 'output'
            print_node(ch, module, fd, newprefix, path, mode, depth, width)

def print_node(s, module, fd, prefix, path, mode, depth, width):
    #fd.write("%s%s--" % (prefix[0:-1], get_status_str(s)))
    fd.write("%s<tr>\n" % prefix[0:-1])

    if s.i_module.i_modulename == module.i_modulename:
        name = s.arg
    else:
        name = s.i_module.i_prefix + ':' + s.arg
    flags = get_flags_str(s, mode)
    if s.keyword == 'list':
        name += '*'
        pass #fd.write(flags + " " + name)
    elif s.keyword == 'container':
        p = s.search_one('presence')
        if p is not None:
            name += '!'
            fd.write("%s<td>\n" % prefix)
            fd.write("%s  name\n" % (prefix, name))
            fd.write("%s<td>\n" % prefix)
        pass #fd.write(flags + " " + name)
    elif s.keyword  == 'choice':
        m = s.search_one('mandatory')
        if m is None or m.arg == 'false':
            pass #fd.write(flags + ' (' + name + ')?')
        else:
            pass #fd.write(flags + ' (' + name + ')')
    elif s.keyword == 'case':
        pass #fd.write(':(' + name + ')')
    else:
        if s.keyword == 'leaf-list':
            name += '*'
        elif (s.keyword == 'leaf' and not hasattr(s, 'i_is_key')
              or s.keyword == 'anydata' or s.keyword == 'anyxml'):
            m = s.search_one('mandatory')
            if m is None or m.arg == 'false':
                name += '?'
        t = get_typename(s)
        if t == '':
            pass #fd.write("%s %s" % (flags, name))
        else:
            pass #fd.write("%s %-*s   %s" % (flags, width+1, name, t))

    if s.keyword == 'list' and s.search_one('key') is not None:
        pass #fd.write(" [%s]" % re.sub('\s+', ' ', s.search_one('key').arg))

    features = s.search('if-feature')
    if len(features) > 0:
        pass #fd.write(" {%s}?" % ",".join([f.arg for f in features]))

    pass #fd.write('\n')
    fd.write("%s</tr>\n" % prefix[0:-1])
    if hasattr(s, 'i_children'):
        if depth is not None:
            depth = depth - 1
        chs = s.i_children
        if path is not None and len(path) > 0:
            chs = [ch for ch in chs
                   if ch.arg == path[0]]
            path = path[1:]
        if s.keyword in ['choice', 'case']:
            print_children(chs, module, fd, prefix, path, mode, depth, width)
        else:
            print_children(chs, module, fd, prefix, path, mode, depth)

def get_status_str(s):
    status = s.search_one('status')
    if status is None or status.arg == 'current':
        return '+'
    elif status.arg == 'deprecated':
        return 'x'
    elif status.arg == 'obsolete':
        return 'o'

def get_flags_str(s, mode):
    if mode == 'input':
        return "-w"
    elif s.keyword in ('rpc', 'action', ('tailf-common', 'action')):
        return '-x'
    elif s.keyword == 'notification':
        return '-n'
    elif s.i_config == True:
        return 'rw'
    elif s.i_config == False or mode == 'output' or mode == 'notification':
        return 'ro'
    else:
        return '--'

def get_typename(s):
    t = s.search_one('type')
    if t is not None:
        if t.arg == 'leafref':
            p = t.search_one('path')
            if p is not None:
                # Try to make the path as compact as possible.
                # Remove local prefixes, and only use prefix when
                # there is a module change in the path.
                target = []
                curprefix = s.i_module.i_prefix
                for name in p.arg.split('/'):
                    if name.find(":") == -1:
                        prefix = curprefix
                    else:
                        [prefix, name] = name.split(':', 1)
                    if prefix == curprefix:
                        target.append(name)
                    else:
                        target.append(prefix + ':' + name)
                        curprefix = prefix
                return "-> %s" % "/".join(target)
            else:
                return t.arg
        else:
            return t.arg
    else:
        return ''
