""" this tool extracts information from cadsoft's eagle .brd and .sch
files to build a bill-of material
"""

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import csv
import sys
from itertools import groupby
import getopt
import re

column_sort_dict = {
        'NAME':0,
        'COUNT':1,
        'VALUE':2,
        'PACKAGE':3,
        'DO_NOT_PLACE':4,
        'PROVIDED_BY':5
}

def sort_colums_for_csv(column_name):
    """this is the sort function for the keys (i.e. columns) of the csv file"""

    if column_name in column_sort_dict:
        return column_sort_dict[column_name]
    else:
        return ord(column_name[0]) + 99

def sort_dict_by_all_but_name(part):
    """this is the sort and group function that is used for grouping the parts 
    by value, but only if all of the other parameters are identical"""
    part_cpy = part.copy()
    part_cpy['NAME'] = ''
    part_string = str(part_cpy)
    return part_string

def sort_rows_for_csv(part):
    """this is the sort function that is used to determine the order of the
    lines of the csv"""
    if (part['NAME'].find(',')):
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
            if (not key in keys):
                keys.append(key)
    return keys

def write_value_list(elements, filename, set_delimiter):
    """group elements by value if they have the same attributes otherwise
    and write to 'filename' as csv file"""
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
        count = 1
        for element in group:
            grouped_element['NAME'] += ','+element['NAME']
            count += 1
        grouped_element['COUNT'] = count
        grouped_elements.append(grouped_element)
    return write_part_list(grouped_elements, filename, set_delimiter)


def write_part_list(elements, filename, set_delimiter):
    """write elements to csv without grouping them i.e. this will be one
    line per component"""
    keys = get_keys_from_dict_list(elements)

    #remove fix position columns from keys, remember those in separate list
    fix_position_keys = []
    for key in column_sort_dict:
      if key in keys:
        fix_position_keys.append(key)
        keys.remove(key)

    fix_position_keys.sort(key=sort_colums_for_csv)
    keys.sort()
    all_keys_sorted = fix_position_keys + keys
    elements.sort(key=sort_rows_for_csv)
    file_pointer = open(filename, 'w')
    dict_writer = csv.DictWriter(file_pointer, all_keys_sorted, delimiter=set_delimiter,
                                 lineterminator = '\n')

    dict_writer.writer.writerow(all_keys_sorted)
    dict_writer.writerows(elements)
    return 0

def usage():
    """print usage messages to the command line"""
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
    print("\t-t / --type=\t\t specify the type ('value' or 'part' are valid "\
              "values) of the output csv, default:part")
    print("\t-v / --variant=\t\t specify which variant should be used, "\
              "default is to use the active variant as saved in the board file")
    print("\t--separator=\t\t specify the separator that should be used as "\
              "delimiter between each column in the output csv file, use 'TAB'"\
              "to specify tabulator as separator")
    print("\t--notestpads\t\t excludes all parts that have a attriute "\
              "'TP_SIGNAL_NAME' with a value")
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

def get_librarypart(drawing, library, deviceset):
    """get the library part from input parameters drawing, library and deviceset
    NOTE: works for schematic trees only"""
    for library_tree in drawing.iterfind('schematic/libraries/library'):
        if (library_tree.attrib['name'] == library):
            for deviceset_tree in library_tree.iterfind('devicesets/deviceset'):
                if (deviceset_tree.attrib['name'] == deviceset):
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
        if (variant.attrib['name'] == selected_variant):
            if ('value' in variant.attrib):
                part['VALUE'] = variant.attrib['value']
            if ('populate' in variant.attrib):
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
        if (('current' in elem.attrib) and (elem.attrib['current']=="yes")):
            default_variant = elem.attrib['name']
        if (elem.attrib['name'] == settings['set_variant']):
            selected_variant = settings['set_variant']
            
    #find out which variant to use, if there is any
    if (selected_variant == "" and
        default_variant == "" and
        number_variant > 0):
        print ("invalid variant defined, aborting")
        return
    elif (selected_variant == ""):
        selected_variant = default_variant

    if (number_variant > 0):
        print ("variant: " + selected_variant)

    return selected_variant

def bom_creation(settings):
    """ this function reads the eagle XML and processes it to produce the
    bill of material
    """
     
    #prepare differences for brd and sch files
    if ('in_filename_brd' in settings):
        tree = ET.ElementTree(file=settings['in_filename_brd'])
        variant_find_string = "board/variantdefs/variantdef"            
        part_find_string = "board/elements/element"
    elif ('in_filename_sch' in settings):
        tree = ET.ElementTree(file=settings['in_filename_sch'])
        variant_find_string = "schematic/variantdefs/variantdef"
        part_find_string = "schematic/parts/part"

    root = tree.getroot()
    drawing = root[0]
    elements = []

    #select which variant to use
    selected_variant = select_variant(drawing, variant_find_string, settings)

    #read all elements that are on the board
    for elem in drawing.iterfind(part_find_string):
        element = {}
        element['NAME'] = elem.attrib['name']
        
        if ("value" in elem.attrib):
            element['VALUE'] = elem.attrib['value']
        if ("package" in elem.attrib):
            element['PACKAGE'] = elem.attrib['package']
            
        # only try to get description if we use the schematic...
        # the BRD file does not contain this information
        if ('in_filename_sch' in settings):
            description = get_description(drawing,
                                        elem.attrib['library'],
                                        elem.attrib['deviceset'])
            description = get_first_line_text_from_html(description)
            element['DESCRIPTION'] = description
        
            element['DEVICE'] = elem.attrib["device"]
            element['PACKAGE'] = get_package(drawing,
                                    elem.attrib['library'],
                                    elem.attrib['deviceset'],
                                    elem.attrib['device'])
            
        #get all attributes of the element
        for attribute in elem.iterfind('attribute'):
            if ('value' in attribute.attrib):
                attribute_name = attribute.attrib['name'].upper()
                attribute_value = attribute.attrib['value']
                element[attribute_name] = attribute_value
        change_part_by_variant(elem, element, selected_variant)
        if ('EXCLUDEFROMBOM' not in element and
        (('in_filename_sch' in settings and is_part_on_pcb(drawing,
        elem.attrib['library'],
        elem.attrib['deviceset'])
        ) or 'in_filename_brd' in settings)):
            if((settings['notestpads'] == False) or ('TP_SIGNAL_NAME' not in element)):
                elements.append(element)

    print("writing bom of type " + settings['bom_type'])
    if (settings['bom_type']=='value'):
        write_value_list(elements, settings['out_filename'],
                         settings['set_delimiter'])
    elif (settings['bom_type']=='part'):
        write_part_list(elements, settings['out_filename'],
                        settings['set_delimiter'])

def parse_command_line_arguments(argv):
    """parses the command line arguments according to usage print
    and returns everything in an associative array
    """
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
                                    "notestpads"])[0]
    except getopt.GetoptError:                     
        usage()                                                    
        sys.exit(2)         

    for opt, arg in opts:                                
        if opt in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif opt in("--notestpads"):
            settings['notestpads'] = True
        elif opt in ("-c", "--csv"):
            settings['out_filename'] = arg
        elif opt in ("-b", "--brd"):
            settings['in_filename_brd'] = arg
        elif opt in ("-s", "--sch"):
            settings['in_filename_sch'] = arg
        elif opt in ("-t", "--type"):
            settings['bom_type'] = arg
        elif opt in ("-v", "--variant"):
            settings['set_variant'] = arg
        elif opt in ("--separator"):
            if (arg == "TAB"):
                settings['set_delimiter'] = '\t'
            else:
                settings['set_delimiter'] = arg

    return settings

def main(argv):
    """ main function """

    settings = parse_command_line_arguments(argv)

    #check sanity of settings
    if ('set_delimiter' not in settings):
        print("defaulting to separator \",\"")
        settings['set_delimiter'] = ','

    if ('in_filename_brd' not in settings
        and 'in_filename_sch' not in settings):
        usage()
        sys.exit(3)

    if ('out_filename' not in settings):
        usage()
        sys.exit(4)

    if ('bom_type' not in settings):
        print("defaulting to bom type 'part'")
        settings['bom_type'] = 'part'

    if not 'set_variant' in settings:
        settings['set_variant'] = ''


    bom_creation(settings)

if __name__ == "__main__":
    main(sys.argv[1:])
