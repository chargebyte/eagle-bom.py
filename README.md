eagle-bom.py
============

**This script is a replacement of the eagle ulp that creates a bom.**

- We wrote it to get better bill of materials than the eagle ulp generates. Especially when you group the lines of your bom by part values the bundled ulp did not compare the attributes for each part. This could lead to loss of attributes. This can happen when you use 100nF capacitors at 3.3V and 50V in the same schematic and you use the attributes to specify the parameters of each part.
eagle-bom.py solves this problem by grouping only parts with identical sets of attributes.
- Another point where an external tool for the creation of a bill of material is usefull is the automatic generation of the bom.

You can use eagle-bom.py as follows:
------------------------------------

execute the script: "python eagle-bom.py"

this will give you a usage help as this:
usage: 
	mandatory arguments
	-c / --csv=		 csv where you want to store the BOM
	exclusive mandatory arguments (i.e. choose one of the following)
	-b / --brd=		 eagle board file that you want to use as input for the BOM
	-s / --sch=		 eagle schematic file that you want to use as input for the BOM
	
	optional arguments
	-h / --help		 print this help
	-t / --type=		 specify the type ('value' or 'part' are valid values) of the output csv, default:part
	-v / --variant=		 specify which variant should be used, default is to use the active variant as saved in the board file
	--separator=		 specify the separator that should be used as delimiter between each column in the output csv file, use 'TAB'to specify tabulator as separator
	--notestpads		 excludes all parts that have a attriute 'TP_SIGNAL_NAME' with a value
	
	
	special attributes for EAGLE parts that are interpreted by this script:
		EXCLUDEFROMBOM		parts with this attribute set to a value other than blank will be excluded from the bom
		DO_NOT_PLACE		usually should have the value 'yes' for instructing the manufacturer to leave this part unplaced
		PROVIDED_BY		specify where the manufacturer gets the parts from
		additionally DNP markings from eagle variants are converted to use the DO_NOT_PLACE format
