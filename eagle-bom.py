""" this tool extracts information from cadsoft's eagle .brd and .sch
files to build a bill-of material
"""

#for compatibility between python2 and python3 in conjunction with pylint
from __future__ import print_function

__version__ = "0.2.0"

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import csv
import sys
from itertools import groupby
import getopt
import re
import cairo
import math

COLUMNFIXEDORDER = {
        'NAME':0,
        'COUNT':1,
        'VALUE':2,
        'PACKAGE':3,
        'DO_NOT_PLACE':4,
        'PROVIDED_BY':5
}

VALID_BOM_TYPES = ("value", "part", "sticker")

# Label settings (all dimensions in mm)
LABEL_WIDTH = 72
LABEL_HEIGHT = 63.5
LABELS_X = 4
LABELS_Y = 3
MARGIN_TOP = 7.75
MARGIN_LEFT = 4.5
SPACING_X = 0.0
SPACING_Y = 2.0
PAGE_WIDTH = 297
PAGE_HEIGHT = 210

class Module:
    def __init__(self, mod, lib):
        self.location = []
        self.ref = ""
        self.lines = []
        self.circs = []
        self.bounds = []
        self._parse(mod, lib)

    def render(self, cr):
        """"
        Render the footprint in the board coordinate system.
        """
        #if package is on bottom do not render anything
        if len(self.location) == 4 and self.location[3] == True:
            return

        cr.save()
        cr.translate(self.location[0], self.location[1])
        cr.set_line_width(0.05)
        if len(self.location) >= 3:
            cr.rotate(-self.location[2] * math.pi/180)
        if self.lines or self.circs:
            for line in self.lines:
                cr.move_to(*line[0])
                cr.line_to(*line[1])
                cr.stroke()
            for circ in self.circs:
                cr.new_sub_path()
                cr.arc(circ[0][0], circ[0][1], circ[1], 0, 2*math.pi)
        cr.restore()

    def render_highlight(self, cr):
        """
        Render a highlight at the footprint's position and of its size.
        """
        #if package is on bottom do not render anything
        if len(self.location) == 4 and self.location[3] == True:
            return

        cr.save()
        cr.translate(self.location[0], self.location[1])
        if len(self.location) >= 3:
            cr.rotate(-self.location[2] * math.pi/180)
        start_x, start_y, end_x, end_y = self.bounds
        margin = 0.2
        start_x -= margin
        start_y -= margin
        end_x += margin
        end_y += margin
        radius = 0.5
        pi2 = math.pi / 2.0
        cr.new_sub_path()
        cr.arc(start_x+radius, start_y+radius, radius, 2*pi2, 3*pi2)
        cr.arc(end_x-radius, start_y+radius, radius, 3*pi2, 4*pi2)
        cr.arc(end_x-radius, end_y-radius, radius, 0*pi2, 1*pi2)
        cr.arc(start_x+radius, end_y-radius, radius, 1*pi2, 2*pi2)
        cr.close_path()
        cr.fill()
        cr.restore()

    def _parse(self, mod, libs):
        mod_library = mod.attrib['library']
        mod_footprint = mod.attrib['package']
        self.location = [float(mod.attrib['x']), -float(mod.attrib['y'])]
        self.ref = mod.attrib['name']
        mirrored = False
        angle = 0
        if "rot" in mod.attrib:
            rot = mod.attrib['rot']
            if rot[0] == "M":
                mirrored = True
                angle = float(rot[2:])
            else:
                angle = float(rot[1:])
        self.location.append(angle)
        self.location.append(mirrored)
        self.bounds = [None, None, None, None]
        for library in libs.iterfind("library"):
            if library.attrib['name'] == mod_library:
                for footprint in library.iterfind("packages/package"):
                    if footprint.attrib['name'] == mod_footprint:
                        self._parse_graphic(footprint)
        if self.bounds[0] == None:
            self.bounds[0] = 0
            self.bounds[1] = 0
            self.bounds[2] = 0
            self.bounds[3] = 0


    def _rotate_point(self.point, pivot, angle):
        sin = math.sin(math.radians(angle))
        cos = math.cos(math.radians(angle))
        #translate point back to origin:
        point[0] -= pivot[0]
        point[1] -= pivot[1]
        #rotate point
        new_point = [0, 0]
        new_point[0] = point[0] * cos - point[1] * sin
        new_point[1] = point[0] * sin + point[1] * cos
        point = new_point
        #translate point back:
        point[0] += pivot[0]
        point[1] += pivot[1]
        return point

    def _parse_graphic(self, footprint):
        for wire in footprint.iterfind("wire"):
            if wire.attrib['layer'] in ('21', '51'):
                start = (float(wire.attrib['x1']), -float(wire.attrib['y1']))
                end = (float(wire.attrib['x2']), -float(wire.attrib['y2']))
                self._update_bounds(start)
                self._update_bounds(end)
                self.lines.append((start, end))
        for rectangle in footprint.iterfind("rectangle"):
            if rectangle.attrib['layer'] in ('21', '51'):
                start_x = float(rectangle.attrib['x1'])
                end_x = float(rectangle.attrib['x2'])
                start_y = float(rectangle.attrib['y1'])
                end_y = float(rectangle.attrib['y2'])
                start = [start_x, -start_y]
                end = [end_x, -end_y]
                if "rot" in rectangle.attrib:
                    angle = float(rectangle.attrib['rot'][1:])
                    center = [(start[0]+end[0])/2, (start[1]+end[1])/2]
                    start = self._rotate_point(start, center, angle)
                    end = self._rotate_point(end, center, angle)
                self._update_bounds(start)
                self._update_bounds(end)
                self.lines.append((start, (end[0], start[1])))
                self.lines.append(((end[0], start[1]), end))
                self.lines.append((end, (start[0], end[1])))
                self.lines.append(((start[0], end[1]), start))
        for circle in footprint.iterfind("circle"):
            if circle.attrib['layer'] in ('21', '51'):
                center = (float(circle.attrib['x']), float(circle.attrib['y']))
                radius = float(circle.attrib['radius'])
                self._update_bounds((center[0]-radius, center[1]-radius))
                self._update_bounds((center[0]+radius, center[1]+radius))
                self.circs.append((center, radius))

    def _update_bounds(self, location):
        if self.bounds[0] == None:
            self.bounds[0] = location[0]
            self.bounds[1] = location[1]
            self.bounds[2] = location[0]
            self.bounds[3] = location[1]
        self.bounds[0] = min(self.bounds[0], location[0])
        self.bounds[1] = min(self.bounds[1], location[1])
        self.bounds[2] = max(self.bounds[2], location[0])
        self.bounds[3] = max(self.bounds[3], location[1])

class PCB:
    def __init__(self, board):
        self.modules = []
        self.edge_lines = []
        self.edge_arcs = []
        self._parse(board)

    def render(self, cr, where, max_w, max_h, highlights=None):
        """
        Render the PCB, with the top left corner at `where`,
        occupying at most `max_w` width and `max_h` height,
        and draw a highlight under parts whose reference is in `highlights`.
        """
        cr.save()
        cr.set_line_width(0.1)

        # Set a clip to ensure we occupy at most max_w and max_h
        cr.rectangle(where[0], where[1], max_w, max_h)
        cr.clip()

        # Find bounds on highlighted modules
        hl_bounds = self._find_highlighted_bounds(highlights)
        bound_width = hl_bounds[2] - hl_bounds[0]
        bound_height = hl_bounds[3] - hl_bounds[1]
        bound_centre_x = hl_bounds[0] + bound_width/2
        bound_centre_y = hl_bounds[1] + bound_height/2

        # Scale to fit bounds
        if bound_width > 0 and bound_height > 0:
            scale_x = max_w / bound_width
            scale_y = max_h / bound_height
            scale = min(scale_x, scale_y, 3)
            cr.scale(scale, scale)
        else:
            scale = 1

        # Can we shift the top edge of the PCB to the top and not cut off
        # the bottom of the highlight?
        if hl_bounds[3] - self.bounds[1] < max_h/scale:
            shift_y = -self.bounds[1]

        # Can we shift the bottom edge of the PCB to the bottom and not cut off
        # the top of the highlight?
        elif self.bounds[3] - hl_bounds[1] < max_h/scale:
            shift_y = -self.bounds[3] + max_h/scale

        # Otherwise centre the highlighted region vertically
        else:
            shift_y = (max_h/(2*scale))-bound_centre_y

        # Can we shift the left edge of the PCB to the left and not cut off
        # the right of the highlight?
        if hl_bounds[2] - self.bounds[0] < max_w/scale:
            shift_x = -self.bounds[0]

        # Can we shift the right edge of the PCB to the right and not cut off
        # the left of the highlight?
        elif self.bounds[2] - hl_bounds[0] < max_w/scale:
            shift_x = -self.bounds[2] + max_w/scale

        # Otherwise centre the highlighted region horizontally
        else:
            shift_x = (max_w/(2*scale))-bound_centre_x

        cr.translate(shift_x, shift_y)

        # Translate our origin to desired position on page
        cr.translate(where[0]/scale, where[1]/scale)

        # Render highlights below everything else
        cr.set_source_rgb(1.0, 0.5, 0.5)
        for module in self.modules:
            if module.ref in highlights:
                module.render_highlight(cr)

        # Render modules
        cr.set_source_rgb(0, 0, 0)
        for module in self.modules:
            module.render(cr)

        # Render edge lines
        for line in self.edge_lines:
            cr.move_to(*line[0])
            cr.line_to(*line[1])
            cr.stroke()

        # Render edge arcs
        for arc in self.edge_arcs:
            cr.new_sub_path()
            cr.arc(*arc)
            cr.stroke()

        cr.restore()

    def _find_highlighted_bounds(self, highlights):
        # Find bounds on highlighted modules
        # TODO: Deal with rotation in modules in a more elegant fashion
        # (Rotation includes bounds, so here we just take the biggest bound,
        #  which is both wasteful for high aspect ratio parts, and wrong for
        #  parts not on a 90' rotation).
        hl_bounds = [self.bounds[2], self.bounds[3],
                     self.bounds[0], self.bounds[1]]
        for module in self.modules:
            if module.ref not in highlights:
                continue
            a = max(module.bounds) * 2
            hl_bounds[0] = min(hl_bounds[0], module.location[0] - a)
            hl_bounds[1] = min(hl_bounds[1], module.location[1] - a)
            hl_bounds[2] = max(hl_bounds[2], module.location[0] + a)
            hl_bounds[3] = max(hl_bounds[3], module.location[1] + a)
        return hl_bounds

    def _parse(self, board):
        self.bounds = self._parse_edges(board)

        #TODO: bounds should be updated if parts overlap the PCB outline
        libraries = board.find("board/libraries")
        for module in board.iterfind("board/elements/element"):
            self.modules.append(Module(module, libraries))

        self.width = self.bounds[2] - self.bounds[0]
        self.height = self.bounds[3] - self.bounds[1]

    def _get_angle(self, start, end):
        start_x = start[0]
        start_y = start[1]
        end_x = end[0]
        end_y = end[1]
        x_diff = end_x-start_x
        y_diff = end_y-start_y

        if x_diff != 0:
            angle = math.degrees(math.atan(y_diff / x_diff))
        else:
            angle = 90

        if end_x < start_x:
            angle += 180
        elif end_x == start_x and end_y < start_y:
            angle += 180

        return angle

    def _add_curved_line(self, start, end, curve):
        start_x = start[0]
        start_y = start[1]
        end_x = end[0]
        end_y = end[1]
        #middle between start and end point
        x_mid = (start_x + end_x) / 2
        y_mid = (start_y + end_y) / 2

        #difference between the points to calculate the angle of the direct line
        angle = self._get_angle([start_x, start_y], [end_x, end_y])


        #add angle between mid and center points which is 90 degrees
        angle += 90

        #distance from point 1 to the middle point
        dist_1_mid = ((start_x-x_mid)**2 + (start_y-y_mid)**2)**0.5

        #distance from the middle point to the center of the circle
        dist_mid_center = dist_1_mid / math.tan(math.radians(curve/2))

        x_center = x_mid + dist_mid_center * math.cos(math.radians(angle))
        y_center = y_mid + dist_mid_center * math.sin(math.radians(angle))

        radius = ((x_center - start_x)**2 + (y_center - start_y)**2)**0.5

        #get angle from center to start and end
        angle_start = self._get_angle([x_center, y_center], [start_x, start_y])
        angle_end = self._get_angle([x_center, y_center], [end_x, end_y])

        if curve > 0:
            self.edge_arcs.append((x_center, y_center, radius,
                           math.radians(angle_start), math.radians(angle_end)))
        else:
            self.edge_arcs.append((x_center, y_center, radius,
                           math.radians(angle_end), math.radians(angle_start)))

    def _parse_edges(self, board):
        min_x = None
        max_x = None
        min_y = None
        max_y = None
        for line in board.iterfind("board/plain/wire"):
            if "layer" in line.attrib and line.attrib['layer'] == "20":
                x1 = float(line.attrib['x1'])
                x2 = float(line.attrib['x2'])
                y1 = -float(line.attrib['y1'])
                y2 = -float(line.attrib['y2'])
                if "curve" in line.attrib:
                    curve = -float(line.attrib['curve'])
                else:
                    curve = 0.0
                if min_x == None:
                    min_x = x1
                    max_x = x1
                    min_y = y1
                    max_y = y1

                min_x = min(x1, min_x)
                min_x = min(x2, min_x)
                max_x = max(x1, max_x)
                max_x = max(x2, max_x)

                min_y = min(y1, min_y)
                min_y = min(y2, min_y)
                max_y = max(y1, max_y)
                max_y = max(y2, max_y)

                start = [x1, y1]
                end = [x2, y2]

                if curve == 0:
                    self.edge_lines.append((start, end))
                else:
                    self._add_curved_line(start, end, curve)

        return [min_x, min_y, max_x, max_y]


class Line:
    def __init__(self, refs, value, footprint, supplier, code):
        self.refs = refs
        self.value = value
        self.footprint = footprint
        self.supplier = supplier
        self.code = code

    def render(self, cr, where, w, h):
        cr.save()

        # Clip to permissible area
        cr.rectangle(where[0], where[1], w, h)
        cr.clip()

        # Draw first line
        cr.set_source_rgb(0, 0, 0)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL,
                            cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(3.0)
        cr.move_to(where[0]+3, where[1]+5)
        cr.show_text(" ".join(self.refs))

        # Draw second line
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL,
                            cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(3.0)
        cr.move_to(where[0]+3, where[1]+9)
        cr.show_text("{}x  {}  {}"
                     .format(len(self.refs), self.value, self.footprint))

        # Draw third line
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL,
                            cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(3.0)
        cr.move_to(where[0]+3, where[1]+12)
        cr.show_text("{} {}".format(self.supplier, self.code))

        cr.restore()


def sort_colums_for_csv(column_name):
    """this is the sort function for the keys (i.e. columns) of the csv file"""

    if column_name in COLUMNFIXEDORDER:
        return COLUMNFIXEDORDER[column_name]
    else:
        return ord(column_name[0]) + 99

def sort_dict_by_all_but_name(part):
    """this is the sort and group function that is used for grouping the parts
    by value, but only if all of the other parameters are identical"""
    part_cpy = part.copy()
    part_cpy['NAME'] = ''
    part_string = str(sorted(part_cpy.items()))
    return part_string

def sort_rows_for_csv(part):
    """this is the sort function that is used to determine the order of the
    lines of the csv"""
    if part['NAME'].find(','):
        stri = part['NAME'].split(',')[0]
    else:
        stri = part['NAME']
    if 'DO_NOT_PLACE' in part:
        return '0'
    if 'PROVIDED_BY' in part:
        return '1'
    return ''.join(c for c in stri if not c.isdigit())

def sort_dict_name_by_number(part):
    """this is the sort function used for sorting the names within a group"""
    count = 0
    for character in part['NAME']:
        if character.isdigit():
            count += 1

    if count == 0:
        return 0
    else:
        return int(''.join(character for character
                           in part['NAME'] if character.isdigit()))

def get_keys_from_dict_list(elements):
    """find all used keys that are used in a list of dictionaries"""
    keys = []
    for element in elements:
        element_keys = element.keys()
        for key in element_keys:
            if not key in keys:
                keys.append(key)
    return keys

def get_value_list(elements):
    """group elements by value if they have the same attributes otherwise
    and return the elements list reduced to one line per different component
    where the NAME field will be a list of all parts that are using the same
    component"""
    elements.sort(key=sort_dict_by_all_but_name)

    groups = []
    uniquekeys = []
    for key, group in groupby(elements, key=sort_dict_by_all_but_name):
        groups.append(list(group))        # Store group iterator as a list
        uniquekeys.append(key)

    grouped_elements = []
    for group in groups:
        group.sort(key=sort_dict_name_by_number)
        grouped_element = group.pop(0)
        first_name = grouped_element['NAME']
        grouped_element['NAME'] = list()
        grouped_element['NAME'].append(first_name)
        count = 1
        for element in group:
            grouped_element['NAME'].append(element['NAME'])
            count += 1
        grouped_element['COUNT'] = count
        grouped_elements.append(grouped_element)
    return grouped_elements

def sheet_positions(cr, label_width, label_height, labels_x, labels_y,
                    margin_top, margin_left, spacing_x, spacing_y):
    """Forever yields a new (x, y) of successive label top-left positions,
    calling cr.show_page() when the current page is exhausted.
    """
    while True:
        for x in range(labels_x):
            for y in range(labels_y):
                xx = margin_left + x*(label_width + spacing_x)
                yy = margin_top + y*(label_height + spacing_y)
                yield (xx, yy)
        cr.show_page()

def write_sticker_list(elements, filename, pcb):
    """output bom as stickers for each type of component in pdf format"""
    elements_grouped = get_value_list(elements)

    mm_to_pt = 2.835
    ps = cairo.PDFSurface(filename, PAGE_WIDTH*mm_to_pt, PAGE_HEIGHT*mm_to_pt)
    cr = cairo.Context(ps)

    # Scale user units to millimetres
    cr.scale(1/0.3528, 1/0.3528)

    labels = sheet_positions(cr, LABEL_WIDTH, LABEL_HEIGHT,
                             LABELS_X, LABELS_Y, MARGIN_TOP, MARGIN_LEFT,
                             SPACING_X, SPACING_Y)

    bom = []
    for line in elements_grouped:
        if not ("DO_NOT_PLACE" in line and line['DO_NOT_PLACE'] == "yes") and \
           not ("EXCLUDEFROMBOM" in line and line['EXCLUDEFROMBOM'] == "yes"):
            bom_line = Line(line['NAME'],
                            line['VALUE'],
                            line['PACKAGE'],
                            "",
                            "")
            bom.append(bom_line)

    for line, label in zip(bom, labels):
        line.render(cr, (label[0]+1, label[1]), LABEL_WIDTH-2, 14)
        pcb.render(cr, (label[0]+1, label[1]+14), LABEL_WIDTH-2,
                   LABEL_HEIGHT-14, line.refs)
    cr.show_page()

def write_value_list(elements, filename, set_delimiter):
    """group equal elements together and write to 'filename' as csv file
    """
    grouped_elements = get_value_list(elements)
    return write_part_list(grouped_elements, filename, set_delimiter)


def write_part_list(elements, filename, set_delimiter):
    """write elements to csv without grouping them i.e. this will be one
    line per component"""
    keys = get_keys_from_dict_list(elements)

    #remove fix position columns from keys, remember those in separate list
    fix_position_keys = []
    for key in COLUMNFIXEDORDER:
        if key in keys:
            fix_position_keys.append(key)
            keys.remove(key)

    #field 'NAME' can be a list or a string, we always need a string here...
    #joining lists together by using commas
    for element in elements:
        if type(element['NAME']) == list:
            element['NAME'] = ",".join(element['NAME'])

    fix_position_keys.sort(key=sort_colums_for_csv)
    keys.sort()
    all_keys_sorted = fix_position_keys + keys
    elements.sort(key=sort_rows_for_csv)
    file_pointer = open(filename, 'w')
    dict_writer = csv.DictWriter(file_pointer, all_keys_sorted,
                      delimiter=set_delimiter, lineterminator='\n')

    #write header
    dict_writer.writer.writerow(all_keys_sorted)
    #write content row by row
    for row in elements:
        for key, val in row.items():
            #convert strings so that the dict writer can process unicode in
            #python2 try catch is used to avoid crash in python3 because
            #"unicode" is not defined
            try:
                row[key] = val.encode('utf-8') if type(val) is unicode else val
            except NameError:
                continue
        dict_writer.writerow(row)
    return 0

def get_librarypart(drawing, library, deviceset):
    """get the library part from input parameters drawing, library and deviceset
    NOTE: works for schematic trees only"""
    for library_tree in drawing.iterfind('schematic/libraries/library'):
        if library_tree.attrib['name'] == library:
            for deviceset_tree in library_tree.iterfind('devicesets/deviceset'):
                if deviceset_tree.attrib['name'] == deviceset:
                    return deviceset_tree

def get_package(drawing, library, deviceset, device):
    """get the package name of a device from input parameters drawing,
    library, deviceset and device
    NOTE: works for schematic trees only"""
    deviceset_tree = get_librarypart(drawing, library, deviceset)
    for device_tree in deviceset_tree.iterfind('devices/device'):
        if device_tree.attrib['name'] == device:
            if "package" in device_tree.attrib:
                return device_tree.attrib['package']
    return ""

def get_device_tree(deviceset_tree, device):
    """get the package name of a device from input parameters drawing,
    library, deviceset and device
    NOTE: works for schematic trees only"""
    #print "get_device_tree"
    for device_tree in deviceset_tree.iterfind('devices/device'):
        #print device, device_tree.attrib['name']
        if device_tree.attrib['name'] == device:
            return device_tree
    return None

def get_description(drawing, library, deviceset):
    """get the description of a deviceset from input parameters drawing, library
    and deviceset
    NOTE: works for schematic trees only"""
    deviceset_tree = get_librarypart(drawing, library, deviceset)
    for description in deviceset_tree.iterfind('description'):
        return description.text

def is_part_on_pcb(drawing, library, deviceset):
    """ check weather a part is a schematic only part or if it is also on
    the PCB
    NOTE: works for schematic trees only"""
    deviceset_tree = get_librarypart(drawing, library, deviceset)
    if deviceset_tree.find('devices/device/connects'):
        return True

def change_part_by_variant(part_tree, part, selected_variant):
    """find out if the element has different settings for the selected variant
    and change it accordingly"""

    if 'populate' in part_tree.attrib and part_tree.attrib['populate'] == "no":
        part['DO_NOT_PLACE'] = "yes"
        return

    for variant in part_tree.iterfind('variant'):
        if variant.attrib['name'] == selected_variant:
            if 'value' in variant.attrib:
                part['VALUE'] = variant.attrib['value']
            if 'populate' in variant.attrib:
                part['DO_NOT_PLACE'] = "yes"

def get_first_line_text_from_html(html_string):
    """reduce html to the first line of text and strip all html tags
    """
    if html_string == None:
        return None
    p_div = re.compile(r"</?(p|div|br).*?>",
                       re.IGNORECASE | re.DOTALL)
    html_string = p_div.sub("\n", html_string)
    html_string = re.sub('<[^<]+?>', '', html_string)
    html_string = html_string.split('\n', 1)[0]

    return html_string

def select_variant(drawing, variant_find_string, settings):
    """find all variants that are defined in the drawing
    select the most appropriate one based on settings and default
    variant"""
    ##stores the actual used variant
    selected_variant = ""
    ##stores the default variant if available
    default_variant = ""
    ##stores the number of defined variants in the board file
    number_variant = 0
    #find all variants that are in the schematic
    for elem in drawing.iterfind(variant_find_string):
        number_variant = number_variant + 1
        if ('current' in elem.attrib) and (elem.attrib['current'] == "yes"):
            default_variant = elem.attrib['name']
        if elem.attrib['name'] == settings['set_variant']:
            selected_variant = settings['set_variant']
    #find out which variant to use, if there is any
    if (selected_variant == "" and
        default_variant == "" and
        number_variant > 0):
        print ("invalid variant defined, aborting")
        return
    elif selected_variant == "":
        selected_variant = default_variant

    if number_variant > 0:
        print ("variant: " + selected_variant)

    return selected_variant

def write_bom(elements, settings, pcb):
    """with a prepared list of all BOM elements this function looks at settings
    and calls the matching internal function that exports those list to the
    desired BOM format"""
    print("writing bom of type " + settings['bom_type'])
    if settings['bom_type'] == 'value':
        write_value_list(elements, settings['out_filename'],
                         settings['set_delimiter'])
    elif settings['bom_type'] == 'part':
        write_part_list(elements, settings['out_filename'],
                        settings['set_delimiter'])
    elif settings['bom_type'] == 'sticker':
        write_sticker_list(elements, settings['out_filename'], pcb)

def bom_creation(settings):
    """this function reads the eagle XML and processes it to produce the
    bill of material
    """
    #prepare differences for brd and sch files
    if 'in_filename_brd' in settings:
        root = ET.ElementTree(file=settings['in_filename_brd']).getroot()
        variant_find_string = "board/variantdefs/variantdef"
        part_find_string = "board/elements/element"
        pcb = PCB(root[0])
    elif 'in_filename_sch' in settings:
        root = ET.ElementTree(file=settings['in_filename_sch']).getroot()
        variant_find_string = "schematic/variantdefs/variantdef"
        part_find_string = "schematic/parts/part"

    #if eagleversion was set, just output the used version of eagle and exit
    if 'eagleversion' in settings:
        return output_eagle_version(root)


    drawing = root[0]
    elements = []


    #select which variant to use
    selected_variant = select_variant(drawing, variant_find_string, settings)

    #read all elements that are on the board
    for elem in drawing.iterfind(part_find_string):
        element = {}
        #check if there are attributes in the library and pull them in
        if 'deviceset' in elem.attrib:
            deviceset_tree = get_librarypart(drawing, elem.attrib['library'],
                                             elem.attrib['deviceset'])
            device_tree = get_device_tree(deviceset_tree,
                                          elem.attrib['device'])
            for technology_tree in device_tree.iter('attribute'):
                element[technology_tree.attrib['name']] = \
                                                technology_tree.attrib['value']
        element['NAME'] = elem.attrib['name']
        if "value" in elem.attrib:
            element['VALUE'] = elem.attrib['value']
        if "package" in elem.attrib:
            element['PACKAGE'] = elem.attrib['package']
        # only try to get description if we use the schematic...
        # the BRD file does not contain this information
        if 'in_filename_sch' in settings:
            element['DESCRIPTION'] = get_first_line_text_from_html(
                                        get_description(drawing,
                                            elem.attrib['library'],
                                            elem.attrib['deviceset']))
            element['DEVICE'] = elem.attrib["device"]
            element['PACKAGE'] = get_package(drawing,
                                    elem.attrib['library'],
                                    elem.attrib['deviceset'],
                                    elem.attrib['device'])
        #get all attributes of the element
        for attribute in elem.iterfind('attribute'):
            if 'value' in attribute.attrib:
                attribute_name = attribute.attrib['name'].upper()
                attribute_value = attribute.attrib['value']
                element[attribute_name] = attribute_value
        change_part_by_variant(elem, element, selected_variant)
        if ('EXCLUDEFROMBOM' not in element and (('in_filename_sch' in settings
          and is_part_on_pcb(drawing, elem.attrib['library'],
          elem.attrib['deviceset'])) or 'in_filename_brd' in settings)
          and (settings['notestpads'] == False
          or 'TP_SIGNAL_NAME' not in element)):
            elements.append(element)
    write_bom(elements, settings, pcb)

def output_eagle_version(xml_root):
    """print the version of the eagle file that has been used to generate
    the eagle file
    """
    if "version" in xml_root.attrib:
        print(xml_root.attrib['version'])
        return True

    return False

def usage():
    """print usage messages to the command line"""
    version()
    print("usage: ")
    print("\tmandatory arguments")
    print("\t-c / --csv=\t\t csv where you want to store the BOM")
    print("\texclusive mandatory arguments (i.e. choose one of the following)")
    print("\t-b / --brd=\t\t eagle board file that you want to use as "\
              "input for the BOM")
    print("\t-s / --sch=\t\t eagle schematic file that you want to use "\
              "as input for the BOM")
    print("\t")
    print("\toptional arguments")
    print("\t-h / --help\t\t print this help")
    print("\t-t / --type=\t\t specify the type (valid types are "\
              + ", ".join(VALID_BOM_TYPES) + ""\
              ") of the output, default:part")
    print("\t-v / --variant=\t\t specify which variant should be used, "\
              "default is to use the active variant as saved in the board file")
    print("\t--separator=\t\t specify the separator that should be used as "\
              "delimiter between each column in the output csv file, use 'TAB'"\
              "to specify tabulator as separator")
    print("\t--notestpads\t\t excludes all parts that have a attriute "\
              "'TP_SIGNAL_NAME' with a value")
    print("\t--eagleversion\t\t print the version of eagle that was used to "\
              "generate the board or schematic (only needs arguments for "\
              "board or schematic, not for csv")
    print("\t")
    print("\t")
    print("\tspecial attributes for EAGLE parts that are interpreted by this "\
              "script:")
    print("\t\tEXCLUDEFROMBOM\t\tparts with this attribute set to a value "\
              "other than blank will be excluded from the bom")
    print("\t\tDO_NOT_PLACE\t\tusually should have the value 'yes' for "\
              "instructing the manufacturer to leave this part unplaced")
    print("\t\tPROVIDED_BY\t\tspecify where the manufacturer gets the parts "\
              "from")
    print("\t\tadditionally DNP markings from eagle variants are converted to "\
              "use the DO_NOT_PLACE format")

def version():
    """print version of the script"""
    print("version " + __version__)

def parse_command_line_arguments(argv):
    """parses the command line arguments according to usage print
    and returns everything in an associative array
    """
    #pylint: disable=R0912
    settings = {}
    settings['notestpads'] = False

    try:
        opts = getopt.getopt(argv,
                                   "hc:b:t:s:v:",
                                   ["help", "csv=",
                                    "brd=", "sch=",
                                    "type=",
                                    "separator=",
                                    "variant=",
                                    "notestpads",
                                    "eagleversion",
                                    "version"])[0]
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif opt == "--version":
            version()
            sys.exit(0)
        elif opt in list("--notestpads"):
            settings['notestpads'] = True
        elif opt in ("-c", "--csv"):
            settings['out_filename'] = arg
        elif opt in ("-b", "--brd"):
            settings['in_filename_brd'] = arg
        elif opt in ("-s", "--sch"):
            settings['in_filename_sch'] = arg
        elif opt in ("-t", "--type"):
            if arg in VALID_BOM_TYPES:
                settings['bom_type'] = arg
            else:
                sys.exit(5)
        elif opt in ("-v", "--variant"):
            settings['set_variant'] = arg
        elif opt in list("--separator"):
            if arg == "TAB":
                settings['set_delimiter'] = '\t'
            else:
                settings['set_delimiter'] = arg
        elif opt in list("--eagleversion"):
            settings['eagleversion'] = True

    return settings

def main(argv):
    """ main function """

    settings = parse_command_line_arguments(argv)

    #check sanity of settings
    if ('in_filename_brd' not in settings
        and 'in_filename_sch' not in settings):
        usage()
        sys.exit(3)

    if 'eagleversion' not in settings:
        if 'out_filename' not in settings:
            usage()
            sys.exit(4)

        if 'set_delimiter' not in settings:
            print("defaulting to separator \",\"")
            settings['set_delimiter'] = ','

        if 'bom_type' not in settings:
            print("defaulting to bom type 'part'")
            settings['bom_type'] = 'part'

    if not 'set_variant' in settings:
        settings['set_variant'] = ''

    bom_creation(settings)

if __name__ == "__main__":
    main(sys.argv[1:])
