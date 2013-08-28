_debug = 0

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import csv
import sys
from operator import itemgetter, attrgetter
from itertools import groupby
import string
import getopt

#this is the sort function for the keys (i.e. columns) of the csv file
def sortColumsForCSV(s):
  sort_dict = {'NAME':0, 'COUNT':1, 'VALUE':2, 'PACKAGE':3, 'DO_NOT_PLACE':4, 'PROVIDED_BY':5}
  if s in sort_dict:
    return sort_dict[s]
  else:
    return 99999


#this is the sort and group function that is used for grouping the parts 
#by value, but only if all of the other parameters are identical
def sortDictByAllButName(s):
  s_cpy = s.copy()
  s_cpy['NAME'] = ''
  stri = str(s_cpy)
  return stri

#this is the sort function that is used to determine the order of the lines of the csv
def sortRowsForCVS(s):
  stri = s['NAME'].split(',')[0]
  if 'DO_NOT_PLACE' in s:
    return 0
  if 'PROVIDED_BY' in s:
    return 1
  return ''.join(c for c in stri if not c.isdigit())

#this is the sort function used for sorting the names within a group
def sortDictNameByNumber(s):
  count = 0
  for c in s['NAME']:
    if c.isdigit():
      count += 1;

  if count == 0:
    return 0
  else:
    return int(''.join(c for c in s['NAME'] if c.isdigit()))

#find all used keys that are used in a list of dictionaries
def getKeysFromDictList(elements):
  keys = []
  for element in elements:
    elementKeys = element.keys()
    for key in elementKeys:
      if (not key in keys):
        keys.append(key)
  return keys;

#group elements by value if they have the same attributes otherwise
#and write to 'filename' as csv file
def write_value_list(elements, filename, set_delimiter):
  elements.sort(key=sortDictByAllButName)

  groups = []
  uniquekeys = []
  for k, g in groupby(elements, key=sortDictByAllButName):
     groups.append(list(g))    # Store group iterator as a list
     uniquekeys.append(k)

  groupedElements = []
  for group in groups:
    group.sort(key=sortDictNameByNumber)
    keys = getKeysFromDictList(group)
    groupedElement = group.pop(0)
    count = 1
    for element in group:
      groupedElement['NAME'] += ','+element['NAME']
      count += 1
    groupedElement['COUNT'] = count
    groupedElements.append(groupedElement)
  return write_part_list(groupedElements, filename, set_delimiter)

#write elements to csv without grouping them i.e. this will be one line per component
def write_part_list(elements, filename, set_delimiter):
  keys = getKeysFromDictList(elements)
  #print keys
  keys.sort(key=sortColumsForCSV)
  elements.sort(key=sortRowsForCVS)
  f = open(filename, 'wb')
  dict_writer = csv.DictWriter(f, keys, delimiter=set_delimiter)
  dict_writer.writer.writerow(keys)
  dict_writer.writerows(elements)
  return 0;

def usage():
  print("usage: ")
  print("\tmandatory arguments")
  print("\t-c / --csv=\t\t specify csv in commandline, otherwise you will be asked by a QT Dialog")
  print("\t-b / --brd=\t\t specify eagle board file in commandline, otherwise you will be asked by a QT Dialog")
  print("\t")
  print("\toptional arguments")
  print("\t-d\t\t debug the script (not used yet)")
  print("\t-h / --help\t\t print this help")
  print("\t-t / --type=\t\t specify the type ('value' or 'part' are valid values) of the output csv, default:part")
  print("\t-s / --separator=\t specify the separator that should be used as delimiter between each column in the output csv file")
  print("\t")
  print("\tspecial attributes for EAGLE parts that are interpreted by this script:")
  print("\t\tEXCLUDEFROMBOM\t\tparts with this attribute set to a value other than blank will be excluded from the bom")
  print("\t\tDO_NOT_PLACE\t\tusually should be blank or 'yes' for instructing the manufacturer to leave this part unplaced")
  print("\t\tPROVIDED_BY\t\tspecify where the manufacturer gets the parts from")


def main(argv):

  in_filename = ""
  out_filename = ""
  bom_type = ""
  set_delimiter = ""

  try:                                
    opts, args = getopt.getopt(argv, "hc:b:t:s:", ["help", "csv=", "brd=", "type=", "separator="]) 
  except getopt.GetoptError:           
    usage()                          
    sys.exit(2)     

  for opt, arg in opts:                
    if opt in ("-h", "--help"):
      usage()
      sys.exit()
    elif opt == '-d':
      _debug = 1
    elif opt in ("-c", "--csv"):
      out_filename = arg
    elif opt in ("-b", "--brd"):
      in_filename = arg
    elif opt in ("-t", "--type"):
      bom_type = arg
    elif opt in ("-s", "--separator"):
      if (arg == "TAB"):
        set_delimiter = '\t'
      else:
        set_delimiter = arg

  if (not set_delimiter):
    print("defaulting to separator \",\"")
    set_delimiter = ','

  if (not in_filename):
    usage()
    sys.exit(2)

  if (not out_filename):
    usage()
    sys.exit(2)

  if (not bom_type):
    print("defaulting to bom type 'part'")
    bom_type = 'part'

  tree = ET.ElementTree(file=in_filename)
  root = tree.getroot()
  drawing = root[0]

  elements = []

  #read all elements that are on the board
  for elem in drawing.iterfind('board/elements/element'):
    element = {}
    element['NAME'] = elem.attrib['name'].encode('utf8')
    element['VALUE'] = elem.attrib['value'].encode('utf8')
    element['PACKAGE'] = elem.attrib['package'].encode('utf8')
    for attribute in elem.iterfind('attribute'):
      if ('value' in attribute.attrib):
        element[attribute.attrib['name'].upper()] = attribute.attrib['value'].encode('utf8')
    #TODO: check if attributes are sorted here or we need to do sorting for further actions
    if ('EXCLUDEFROMBOM' not in element):
      elements.append(element)


  print("writing bom of type " + bom_type)
  if (bom_type=='value'):
    write_value_list(elements, out_filename, set_delimiter)
  elif (bom_type=='part'):
    write_part_list(elements, out_filename, set_delimiter)


if __name__ == "__main__":
    main(sys.argv[1:])
