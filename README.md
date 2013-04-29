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

	-d		 debug the script (not used yet)
	-h / --help		 print this help
	-c / --csv=		 specify csv in commandline, otherwise you will be asked by a QT Dialog
	-c / --brd=		 specify eagle board file in commandline, otherwise you will be asked by a QT Dialog
	-t / --type=		 specify the type ('value' or 'part' are valid values) of the output csv, default:part
	
	special attributes for EAGLE parts that are interpreted by this script:
		EXCLUDEFROMBOM		parts with this attribute set to a value other than blank will be excluded from the bom
		DO_NOT_PLACE		usually should be blank or 'yes' for instructing the manufacturer to leave this part unplaced
		PROVIDED_BY		specify where the manufacturer gets the parts from

