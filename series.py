#!/usr/bin/python

#	This file is part of SERIES.
#
#	SERIES is an abstract tool to assist in doing repetitive work
#	on the basis of templates that are copied and individually adapted.
#
#	Copyright (C) 2016 Paul Stephan Weber
#
#	SERIES is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; either version 3 of the License, or
#	(at your option) any later version.
#
#	SERIES is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program; if not, write to the Free Software Foundation,
#	Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA


#
# Options --------------------------------------------------------------
#
version=0.1
dbFile = "series.db"
tmplFile = "template"
buildString = "build"
debug = False

shortOpts = "abdfhimprst:V:C:F:O:T:"
longOpts = [
			"add","all","auto","build","case=",
			"cases","clean","copy=","createDB=","db=",
			"default","delete","exact","export","help","file=","files",
			"force","withOptions","interactive",
			"name=","modify","option=",
			"options","print","reset","run","runFile=","series",
			"template=","type=","value=","version"
			]

seriesOptions = ("runFiles","seriesName","templateFiles","templateString")
metaOptions = ("_caseName","_seriesName")

#
# Functions ------------------------------------------------------------
#
import getopt
import os
import sys
import shutil
import subprocess
import time
import datetime

import sqlite3

# Adds default case and returns its case id
def addCase(caseName):
	if debug: print("addCase:",caseName)

	if (len(caseName) == 0):
		print("Not a valid case name")
		sys.exit(1)

	# Check if case already exists
	if isCase(caseName):
		print("Case "+caseName+" already exists")
		sys.exit(1)

	# Add default case
	cid = addCaseData()

	insert = (caseName,cid)
	sqlCurs.execute('''
		INSERT INTO cases (caseName,currentCid)
		VALUES (?,?);''',insert)

	return cid

# Adds case by copying an existing and returns its cid
def addCaseByCopy(caseName,copyCase):
	# Check if copy case exists and create default
	ccid = verifyCase(copyCase)
	cid = addCase(caseName)

	# Need: fatherCid, oidString, valueString
	sqlCurs.execute('''
		SELECT oidString,valueString
		FROM caseData
		WHERE cid=?''',(ccid,))
	row = sqlCurs.fetchone()

	insert = (ccid,row[0],row[1],cid)
	sqlCurs.execute('''
		UPDATE caseData
		SET fatherCid=?,oidString=?,valueString=?
		WHERE cid=?''',insert)

	return cid

# Adds case by showing a menu for choosing options and returns its cid
def addCaseByMenu(caseName):
	# Create default case
	cid = addCase(caseName)

	# Ask for options and values to set
	vals = []
	oids = []
	while True:
		printOptions('case')

		oid = raw_input("ID of option to add (0 to finish): ")
		try:
			oid = int(oid)
			if (oid == 0): break
			if not isOid(oid): continue
			if oid in oids:
				print("Option already set!")
				continue
		except ValueError:
			print("Give a number please!")
			continue

		val = raw_input("Value to set: ")
		oids.append(str(oid))
		vals.append(str(val))

	# If no option specified there is nothing to do, return
	if (len(oids) == 0): return

	# Build option and value strings and insert
	oidString = ",".join(oids)
	valString = ",".join(vals)

	insert = (oidString,valString,cid)
	sqlCurs.execute('''
		UPDATE caseData
		SET oidString=?, valueString=?
		WHERE cid=?''',insert)

	return cid

# Adds data row in caseData and returns new cid
def addCaseData(fatherCid=0):
	if debug: print("addCaseData: ",fatherCid)
	if fatherCid:
		verifyCid(fatherCid,True)

	# Two possibilities
	#	1:	cid == 0, i.e. fresh case, no father
	#	2:	cid != 0, i.e. not a fresh case, has father

	# Create entry in caseData
	tstamp = int(time.time())
	insert = (fatherCid,tstamp)
	sqlCurs.execute('''
		INSERT INTO caseData (fatherCid,timeCreated)
		VALUES (?,?)''',insert)

	newCid = sqlCurs.lastrowid

	return newCid

# Adds case according to command line parameters
def addCmdCase(caseName):
	# Add by menu
	if isCmdLineArgument('--interactive','-i'):
		addCaseByMenu(caseName)
		
	# Add by copy
	elif isCmdLineArgument('--copy'):
		addCaseByCopy(
			caseName,
			getCmdLineArgument('--copy'),
			)
	
	# Add default case
	else:
		addCase(caseName)
			
# Adds a file to file table and returns its fid
def addFile(newFile):
	if debug: print("addFile: ",newFile)

	if (len(newFile) == 0):
		print("Not a valid file name")
		sys.exit(1)

	if (newFile == 'none'):
		return

	# If file is already non return its fid
	fid = isFile(newFile)
	if fid:
		return fid

	# Find out where file is located
	tmplFid = getTemplateFid(newFile)
	if not tmplFid:
		delFile(newFile,True)
		print("Abort.")
		sys.exit(1)

	# Insert into DB
	insert = (newFile,tmplFid)
	sqlCurs.execute('''
		INSERT INTO files (fileName,templateFid)
		VALUES (?,?)''',insert)
	fid = sqlCurs.lastrowid

	return fid

# Adds file to already set up option
def addFileToOption(optFile,optName):
	oid = verifyOption(optName)

	fid = isFile(optFile)
	if not fid:
		fid = addFile(optFile)

	# Find out if file is already set, if not add, if yes do nothing
	fids = getFidsOfOid(oid)
	if fid in fids:
		return

	else:
		fids.append(fid)
		fidString = ",".join(str(f) for f in fids)

		insert = (fidString,oid)
		sqlCurs.execute('UPDATE options SET fidString=? WHERE oid=?',insert)

# Adds option and default value to series
def addOption(optName,optVal,optType,optFile='none'):
	verifyOptionType(optType)

	if (len(optName) == 0):
		print("Expected option name")
		sys.exit(1)

	# Check if valid meta option


	# Check if option already exists
	if isOption(optName,optType):
		print("Option "+optName+" already available")
		print("To add a file to this option do not specify the default value")
		sys.exit(1)

	# Check if file is given for case options
	if (optType == 'case') and (optFile == 'none'):
		print("Case options need a file")
		sys.exit(1)

	# Add file if given
	fid = addFile(optFile)

	# Insert into db
	insert = (optName,optVal,fid,optType)
	sqlCurs.execute('''
			INSERT INTO options (optionName,defaultValue,fidString,optionType)
			VALUES (?,?,?,?);''',
			insert)

# Adds option and value to case
def addOptionToCase(optName,optValue,caseName,addInstance=True):
	if debug: print("addOptionToCase: ",optName,optValue,caseName,addInstance)
	cid = verifyCase(caseName)

	if isOptionSetForCid(optName,cid):
		print("Option "+optName+" already set for case "+caseName)
		sys.exit(1)

	addOptionToCid(optName,optValue,cid,addInstance)

# Adds option and value to cid
def addOptionToCid(optName,optValue,cid,addInstance=True):
	if debug: print("addOptionToCid: ",optName,optValue,cid,addInstance)
	verifyCid(cid)
	oid = verifyOption(optName)

	if isOptionSetForCid(optName,cid):
		print("Option "+optName+" already set for case id "+str(cid))
		sys.exit(1)

	# Get current option and value string from case
	sqlCurs.execute('SELECT oidString,valueString FROM caseData WHERE cid=?',(cid,))
	row = sqlCurs.fetchone()
	
	# No options set until now
	if (row[0] == None) or (len(row[0]) == 0):
		oidString = str(oid)
		valString = str(optValue).replace(",","_;_")

	# There are already other options, append
	else:
		oidString = row[0] + "," + str(oid)
		valString = row[1] + "," + str(optValue).replace(",","_;_")
	
	# Create new case instance by copy
	if addInstance:
		caseName = getCaseName(cid)
		newCid = addCaseData(cid)
		updateCurrentCid(cid,newCid)
		insert = (oidString,valString,newCid)

	# Retain current id
	else:
		insert = (oidString,valString,cid)

	# Save values for new case instance
	sqlCurs.execute('''
		UPDATE caseData
		SET oidString=?,valueString=?
		WHERE cid=?''',insert)

# Adds option with only type specified
def addOptionWithType(optName,optType):
	verifyOptionType(optType)

	# Adding a meta option
	if (optType == 'meta'):
		if optName not in metaOptions:
			print('Not a valid meta option ('+optName+')')
			sys.exit(1)

		if isCmdLineArgument('--file','-F'):
			fileName = getCmdLineArgument('--file','-F')
		else:
			fileName = 'none'

		addOption(optName,'',optType,fileName)


	# Adding a series option
	elif (optType == 'series'):
		if optName not in seriesOptions:
			print('Not a valid meta option ('+optName+')')
			sys.exit(1)

		# See if value is given
		if isCmdLineArgument('--value','-V'):
			value = getCmdLineArgument('--value','-V')
		else:
			value = ''

		# See if file is given
		if isCmdLineArgument('--file','-F'):
			fileName = getCmdLineArgument('--file','-F')
		else:
			fileName = 'none'

		addOption(optName,optValue,optType,fileName)


	# Do not allow anything else
	else:
		print('Please add as standard option')
		sys.exit(1)

# Adds template file/directory and returns fid
def addTemplate(tmplFile):
	# Check if file is already known to db
	if isFile(tmplFile):
		print("Cannot add file a second time ("+tmplFile+")")
		sys.exit(1)

	# Check if file contains template string
	tmplStr = getValueOfOption('templateString')
	if (tmplFile.find(tmplStr) == -1):
		print('Could not find template string in file name')
		print('String:\t'+tmplStr)
		print('File:\t'+tmplFile)
		sys.exit(1)

	# Find out if file is a directory
	if not os.path.exists(tmplFile):
		print("Not a valid file/directory ("+tmplFile+")")
		sys.exit(1)

	if os.path.isdir(tmplFile):
		isDirectory = 'yes'
	else:
		isDirectory = 'no'

	# Insert template file
	insert = (tmplFile,isDirectory)
	sqlCurs.execute('''
		INSERT INTO files (fileName,isDirectory)
		VALUES (?,?)''',insert)
	fid = sqlCurs.lastrowid

	# Update series option containing all template files
	addFileToOption(tmplFile,'templateFiles')

# Sets options defined for case for given file
def applyOptionsToFile(cid,fileName):
	if debug: print("applyOptionsToFile:",cid,fileName)

	# Build fully qualified name of file
	FQFN = buildFQFN(cid,fileName)

	# Find out which options are to set here
	usedOpts = getOptionsUsedInFile(fileName)
	usedOpts.sort()
	usedOpts.reverse()
	if debug: print("applyOptionsToFile: usedOpts,",usedOpts)

	# Read file into list
	with open(FQFN, "r") as f:
		initial = f.readlines()

	# Empty file and rewrite it line by line
	appliedOpts = []
	with open(FQFN, "w") as f:

		# Handle line after line
		for line in initial:

			# For every option check if it is used in current line
			adaptedLine,optsInLine = applyOptionsToString(cid,usedOpts,line)

			# After every option in this line was handled, write line
			f.write(adaptedLine)

			# Keep track of options used in file
			for o in optsInLine:
				if o not in appliedOpts:
					appliedOpts.append(o)

	# Warn if not every option assigned to this file was set
	for opt in appliedOpts:
		if opt in usedOpts:
			idx = usedOpts.index(opt)
			usedOpts.pop(idx)

	if (len(usedOpts) > 0):
		print("Warning: Options not found in "+fileName+" ("+", ".join(usedOpts)+")")

# Returns a string where all options occuring in input string are
# replaced by their values, as well as a list of options applied
def applyOptionsToString(cid,optsUsedInFile,inputString):
	adaptedString = inputString
	appliedOpts = []

	for opt in optsUsedInFile:

		# If option is found in line
		optStr = 'OPT_'+opt.upper()
		if (adaptedString.find(optStr) != -1):

			# Replace option string by its value
			if isOption(opt,'meta'):
				value = getValueOfMetaOptionOfCid(opt,cid)
			else:
				value = getValueOfOptionOfCid(opt,cid)
			adaptedString = adaptedString.replace(optStr,value)

			# Keep track which options you found in this file
			if opt not in appliedOpts:
				appliedOpts.append(opt)

	# Treat caseName as special option
	#caseName = getCaseName(cid)
	#adaptedString = adaptedString.replace('OPT_CASENAME','OPT_'+caseName.upper())

	return adaptedString,appliedOpts

# Makes copy of template and applies options
def buildCid(cid):
	if debug: print("buildCid:",cid)
	
	# Get case name (verifies cid)
	caseName = getCaseName(cid)
	
	# Copy template files
	buildCaseTree(cid)

	# Get files where options are to be applied
	# File names are not case adapted yet
	optionFiles = getFiles()
	if debug: print("buildCid: optionFiles, ",optionFiles)

	# Go through all files and gather options to set in that file
	for fileName in optionFiles:
		applyOptionsToFile(cid,fileName)

	# Update case entry for last build
	updateCaseBuildData(caseName)

# Creates case tree by copying templates
def buildCaseTree(cid):
	if debug: print("buildCaseTree:",cid)
	
	tmplFiles = getFilesOfOption('templateFiles')

	# Create case files from template files, preserving symlinks
	for tFile in tmplFiles:
		cFile = buildFQFN(cid,tFile)
		bFile = getBuildFile(cFile,tFile)

		# If file is already present
		if os.path.exists(cFile):
			handleTreeBuildingForExistingCase(cid,cFile,bFile)

		# Copy template data to create new case
		if os.path.isdir(tFile):
			#shutil.copytree(tFile,cFile,symlinks=True)		# Preserves symlinks
			shutil.copytree(tFile,cFile)
		else:
			shutil.copy(tFile,cFile)

		# Write build file
		with open(bFile,'w') as f:
			f.write(str(cid))

# Assembles fully qualified file name of file for given cid,
# i.e. the relative path regarding the script execution directory
def buildFQFN(cid,fileName):
	if debug: print("buildFQFN:",cid,fileName)

	# Find out template fid
	fid = verifyFile(fileName)
	sqlCurs.execute('SELECT templateFid FROM files WHERE fid=?',(fid,))
	row = sqlCurs.fetchone()
	tmplFid = row[0]

	# If file is a template file it is already fully qualified
	if (tmplFid == 0):
		FQFN = fileName

	# Prepend template directory to fileName
	else:
		tmplDirName = getFileName(tmplFid)
		FQFN = tmplDirName + "/" + fileName

	# Replace template strings by full case name
	tmplString = getValueOfOption('templateString')
	seriesName = getValueOfOption('seriesName')
	caseName = getCaseName(cid)
	fullCaseName = seriesName + '-' + caseName

	return FQFN.replace(tmplString,fullCaseName)

# Returns options, their values and files for given case
# If includeDefaults=True also options with default values are returned
def buildOptionsForCase(caseName,includeDefaults=False):
	cid = verifyCase(caseName)
	return buildOptionsForCid(cid,includeDefaults)
	
# Returns options, their values and files for given cid
# If includeDefaults=True also options with default values are returned
def buildOptionsForCid(cid,includeDefaults=False):
	optNames = []
	optVals = []
	optFiles = []

	# Get all names of all options
	for row in sqlCurs.execute('''
			SELECT optionName
			FROM options
			WHERE optionType!='series'
			ORDER BY optionName
			'''):
		optNames.append(row[0])

	# Get values and files for all options
	toPop = []
	for opt in optNames:
		if includeDefaults or isOptionSetForCid(opt,cid):
			optVals.append(getValueOfOptionOfCid(opt,cid))
			optFiles.append(getFilesOfOption(opt))
		else:
			idx = optNames.index(opt)
			toPop.append(idx)

	# Pop options which are not to be displayed
	for idx in reversed(toPop):
		optNames.pop(idx)

	return optNames,optVals,optFiles

# Runs a menu to get the file id, return chosen or new file id
def chooseFid():
	print("Known files:")
	printFiles();

	while True:
		try:
			fid = raw_input("Choose file id (0 to add file): ")
			fid = int(fid)
			break
		except ValueError:
			print("Invalid input")

	if isFid(fid):
		return fid
	else:
		name = raw_input("Enter name of file (incl. relative path): ")
		return addFile(name)

# Creates a new database
def createDB(dbName):
	global sqlCurs

	dbFile = dbName + ".db"

	if os.path.isfile(dbFile):
		print("Database already exists ("+dbName+")")
		sys.exit(1)

	sqlCon = sqlite3.connect(dbFile)
	sqlCurs = sqlCon.cursor()

	# Create tables
	createTables()

	# Set initial options
	addOption('seriesName',dbName,'series')
	addOption('templateString','template','series')
	addOption('templateFiles','','series')
	addOption('runFiles','','series')

	# Tell what has to be done
	#print('You need to adjust the templateString before doing anything else')

	sqlCon.commit()
	sqlCon.close()

# Creates tables in fresh data base
def createTables():
	#
	# There are four different tables
	#	options		Stores all possible options and their default values
	#	cases		Stores all case names and the id of current case data
	#	caseData	Stores all specific information about a case
	#	files		Stores all file names and their fid
	#

	# Create table for options and default values
	# Columns:
	#	oid				Id of option
	#	optionName		...
	#	defaultValue	...
	#	fidString		Comma seperated ids of files where this
	#					option is to be applied to
	#	series			Equals 'yes' if option is not for single cases
	#					but for the whole series (like template name)
	sqlCurs.execute('''
		CREATE TABLE options (
			oid				INTEGER PRIMARY KEY AUTOINCREMENT,
			optionName		VARCHAR(50) NOT NULL,
			defaultValue	VARCHAR(50),
			fidString		VARCHAR(50),
			optionType		VARCHAR(50) DEFAULT 'case',
			comment			VARCHAR(1500))
			''')


	# Create table containing cases and their current case id
	# Columns:
	#	caseName	...
	#	currentCid	...
	sqlCurs.execute('''
		CREATE TABLE cases (
			caseName		VARCHAR(100) PRIMARY KEY,
			currentCid		INTEGER NOT NULL,
			comment			VARCHAR(1500))
			''')

	# Create table for case data storing all the options and their
	# values used by each case
	# Columns:
	#	cid				Id of case
	#	fatherCid		Id of father case
	#	timeCreated		Timestamp of creation
	#	timeBuild		Timestamp of last use
	#	oidString		Comma seperated ids of non-default options
	#	valueString		Comma seperated values of options
	#	comment			Could be used for user comments
	sqlCurs.execute('''
		CREATE TABLE caseData (
			cid					INTEGER PRIMARY KEY AUTOINCREMENT,
			fatherCid			INTEGER DEFAULT 0,
			timeCreated			INTEGER NOT NULL,
			timeBuild			INTEGER DEFAULT 0,
			builds				INTEGER DEFAULT 0,
			oidString			VARCHAR(1000),
			valueString			VARCHAR(1000),
			comment				VARCHAR(1500))
			''')


	# Create table for files to be adjusted
	# Columns:
	#	fid			Id of file
	#	fileName	...
	sqlCurs.execute('''
		CREATE TABLE files (
			fid				INTEGER PRIMARY KEY AUTOINCREMENT,
			fileName		VARCHAR(1000) NOT NULL,
			templateFid		INTEGER DEFAULT 0,
			isDirectory		INTEGER DEFAULT 'no'
			)
			''')

# Deletes all files created during build of given case
def delBuildCase(cid,force=False):
	if debug: print("delBuildCase:",cid)

	if not force:
		print("Warning: You are about to delete the build case!")
		answer = raw_input("Proceed? (Y/n): ")
		if (answer != 'Y'):
			print("Abort.")
			sys.exit(0)

	tmplFiles = getFilesOfOption('templateFiles')

	for tFile in tmplFiles:
		cFile = buildFQFN(cid,tFile)
		bFile = getBuildFile(cFile,tFile)
		
		if os.path.isdir(cFile):
			shutil.rmtree(cFile)
		elif os.path.isfile(cFile):
			os.remove(cFile)
		else:
			print('Nothing to delete.')

		if os.path.isfile(bFile):
			os.remove(bFile)

# Deletes given case and all fathers
def delCase(caseName,force=False):
	if debug: print("delCase:",caseName,force)

	if isCmdLineArgument('--force','-f'):
		force = True

	cid = verifyCase(caseName)
	sonsCid = getSonsCid(cid)

	if not force:
		print("Warning: You are about to delete case "+caseName+"!")
		answer = raw_input("Proceed? (Y/n): ")
		if (answer != 'Y'):
			print("Abort.")
			sys.exit(0)

	# Delete case data only if no sons are present, otherwise
	# you would destroy a father-line
	if (len(sonsCid) == 0):
		delCid(cid)

	# Remove case label
	sqlCurs.execute('DELETE FROM cases WHERE currentCid=?',(cid,))

# Deletes given cid and all fathers, not touching case table
def delCid(cid,deleteRecursive=True,depth=0):
	if debug: print("delCid:",cid,deleteRecursive,depth)

	verifyCid(cid)

	fatherCid = getFatherCid(cid)

	siblingsCids = getSiblingsCid(cid)

	# Check if next/recursive call has to be made
	nextCall = True
	
	# Recursion disabled, there is an error somewhere 28.10.14
	nextCall = False

	if not deleteRecursive:
		nextCall = False

	# Do not delete father when there is none
	if not fatherCid:
		nextCall = False

	# Do not delete father if there are siblings
	if (len(siblingsCids) > 1):
		nextCall = False

	# Do not delete father if father is a named case
	if isCid(cid,True) and depth>0:
		nextCall = False

	# Delete father by recursive call
	if nextCall:
		delCid(fatherCid,True,depth+1)

	# After recursive call delete current entry
	sqlCurs.execute('DELETE FROM caseData WHERE cid=?',(cid,))

# Deletes options with default values from case
def delDefaultOptionsFromCase(caseName):
	cid = verifyCase(caseName)
	delDefaultOptionsFromCid(cid)
			
# Deletes options with default values from cid
def delDefaultOptionsFromCid(cid):
	optNames,optVals,optFiles = buildOptionsForCid(cid)
	
	for optName,optVal in zip(optNames,optVals):
		if isDefaultValue(optName,optVal):
			delOptionFromCid(optName,cid,False)

# Removes file
def delFile(fileName,force=False):
	fid = verifyFile(fileName)

	# Delete file from options
	opts = getOptions()
	for o in opts:
		delFileFromOption(o,fileName)

	# Delete file from files table
	sqlCurs.execute('DELETE FROM files WHERE fid=?',(fid,))

# Removes file from already set up option
def delFileFromOption(optName,optFile):
	oid = verifyOption(optName)
	fid = verifyFile(optFile)

	# Get current fidString
	sqlCurs.execute('SELECT fidString FROM options WHERE oid=?',(oid,))
	row = sqlCurs.fetchone()
	fids = row[0].split(',')
	fids = map(int,fids)

	# Find out if file is already set, if yes delete, if not do nothing
	if fid in fids:
		fids.remove(fid)
		fidString = ",".join(str(f) for f in fids)

		insert = (fidString,oid)
		sqlCurs.execute('UPDATE options SET fidString=? WHERE oid=?',insert)

# Deletes given option
def delOption(optName):
	oid = verifyOption(optName)

	print("Warning: Deleting an option leads to unavoidable loss of data!")
	print("If you are not absolutely sure, delete the option from cases instead.")
	answer = raw_input("Proceed? (Y/n): ")
	if (answer != 'Y'):
		print("Abort.")
		sys.exit(0)

	# Run through all cids and remove option from option/valueString
	for row in sqlCurs.execute('''SELECT cid FROM caseData'''):
		cid = row[0]
		if isOptionSetForCid(optName,cid):
			delOptionFromCid(optName,cid,False)

	# Delete option entry
	sqlCurs.execute('DELETE FROM options WHERE oid=?',(oid,))

# Delete option from a case
def delOptionFromCase(optName,caseName,addInstance=True):
	cid = verifyCase(caseName)
	delOptionFromCid(optName,cid,addInstance)

# Delete option from a case with given cid
def delOptionFromCid(optName,cid,addInstance=True):
	oid = verifyOption(optName)
	cid = verifyCid(cid)
	
	if not isOptionSetForCid(optName,cid):
		return

	# Get option and value strings
	sqlCurs.execute('SELECT oidString,valueString FROM caseData WHERE cid=?',(cid,))
	row = sqlCurs.fetchone()
	oids = row[0].split(',')
	oids = map(int,oids)
	vals = row[1].split(',')

	# Remove
	idx = oids.index(oid)
	oids.pop(idx)
	vals.pop(idx)

	# Update
	oidString = ",".join(str(o) for o in oids)
	valString = ",".join(vals)

	# Create or create not new case instance
	if addInstance:
		newCid = addCaseData(cid)
		caseName = getCaseName(cid)
		updateCurrentCid(cid,newCid)
		insert = (oidString,valString,newCid)
	else:
		insert = (oidString,valString,cid)

	# Update DB
	sqlCurs.execute('''
		UPDATE caseData
		SET oidString=?,valueString=?
		WHERE cid=?''',
		insert)
		
def export():
	if debug: print('export')

	# Export first part of series data
	seriesName = getValueOfOption('seriesName')
	templateString = getValueOfOption('templateString')
	print('series --createDB '+seriesName)
	print('series -m -O templateString -V '+templateString)

	# Export files, options and cases
	objects = ['options','files','cases']
	if 'files' in objects:
		exportFiles()
	if 'options' in objects:
		exportOptions()
	if 'cases' in objects:
		exportCases()

	# Export second part of series data
	runFiles = getFilesOfOption('runFiles')
	for f in runFiles:
		print('series -a -O runFiles -F '+f)

def exportCases():
	if debug: print('exportCases')

	allCases = []
	for row in sqlCurs.execute('SELECT caseName FROM cases ORDER BY caseName'):
		allCases.append(row[0])

	for case in allCases:
		print('series -a -C '+case)

		opts,vals,files = buildOptionsForCase(case)
		for o,v in zip(opts,vals):
			print('series -a -C '+case+' -O '+o+" -V \'"+v+"\'")

def exportFiles():
	if debug: print('exportFiles')

	for row in sqlCurs.execute('''
		SELECT fileName,templateFid
		FROM files
		ORDER BY templateFid,fileName'''):
		fileName = row[0]
		templateFid = row[1]

		if not templateFid:
			print('series -a -T '+fileName)
		else:
			print('series -a -F '+fileName)

def exportOptions():
	if debug: print('exportOptions')

	rows = []
	for row in sqlCurs.execute('''
		SELECT optionName,defaultValue,fidString,optionType
		FROM options
		WHERE optionType!='series'
		ORDER BY optionType DESC,optionName'''):
		rows.append(row)

	for row in rows:
		optName = str(row[0])
		optVal = str(row[1])
		optFids = str(row[2])
		optType = str(row[3])

		optFiles = getFilesOfOption(optName)

		if (optType == 'meta'):
			fName = optFiles.pop()

			if (len(optVal) > 0):
				print('series -a -t '+optType+' -O '+optName+" -V \'"+optVal+"\' -F "+fName)
			else:
				print('series -a -t '+optType+' -O '+optName+' -F '+fName)

			for of in optFiles:
				print('series -a -O '+optName+' -F '+of)

		else:
			fName = optFiles.pop()
			print('series -a -O '+optName+" -V \'"+optVal+"\' -F "+fName)
			while optFiles:
				fName = optFiles.pop()
				print('series -a -O '+optName+' -F '+fName)

# Returns lists of options and arguments
def getArgs(shortOpts,longOpts):
	try:
		opts, args = getopt.getopt(
			sys.argv[1:],
			shortOpts,
			longOpts)
	except getopt.GetoptError:
		printHelp()
		sys.exit(1)
	
	# opts: List of (optName, optValue) pairs
	# args: List of arguments that could not be matched with an option
	return opts,args

# Returns cid contained in buildFile
def getBuildCid(buildFile):
	with open(buildFile,'r') as f:
		line = f.readline()
	buildCid = line.strip()

	return int(buildCid)

# Returns file name of build file
def getBuildFile(caseFile,templateFile):
	if isDirectory(templateFile):
		return caseFile + "/." + buildString
	else:
		return "." + buildString + "-" + caseFile

# Returns how often given case was already build
def getCaseBuilds(caseName):
	cid = verifyCase(caseName)

	sqlCurs.execute('SELECT builds FROM caseData WHERE cid=?',(cid,))
	row = sqlCurs.fetchone()
	return row[0]

# Returns case name of case with given id
def getCaseName(cid,isCurrentCid=True):
	if not isCurrentCid:
		print("Cannot lookup caseNames of non-current cids yet (cid: "+caseName+")")
		sys.exit(1)
	
	verifyCid(cid,isCurrentCid)

	sqlCurs.execute('''
		SELECT caseName
		FROM cases
		WHERE currentCid=?''',(cid,))

	row = sqlCurs.fetchone()
	return row[0]

# Returns value of given command line option
def getCmdLineArgument(longOpt,shortOpt="none"):
	# Use global opts variable
	for opt,val in opts:
		if (opt == shortOpt) or (opt == longOpt):
			return val

	print "Missing option ("+longOpt+"/"+shortOpt+")"
	sys.exit(1)

def getDbName(dbFile):
	answer = raw_input("Name for data base (default: "+dbFile+"): ")
	if (len(answer) != 0):
		dbFile = answer

	return dbFile

# Returns father cid of given cid
def getFatherCid(cid):
	if debug: print("getFatherCid: ",cid)
	verifyCid(cid)

	sqlCurs.execute('SELECT fatherCid FROM caseData WHERE cid=?',(cid,))
	row = sqlCurs.fetchone()
	return row[0]

# Returns list of file ids where option with oid has to be set
def getFidsOfOid(oid):
	if debug: print("getFidsOfOid:",oid)

	if not isOid(oid):
		print('Not a valid option id ('+str(oid)+')')
		sys.exit(1)

	sqlCurs.execute('SELECT fidString FROM options WHERE oid=?',(oid,))
	row = sqlCurs.fetchone()

	if (row[0] == None):
		return []

	fids = row[0].split(',')
	try:
		fids = map(int,fids)
	except ValueError:
		return []

	return fids

# Returns fileName belonging to given fid
def getFileName(fid):
	if debug: print('getFileName: ',fid)
	verifyFid(fid)

	sqlCurs.execute('SELECT fileName FROM files WHERE fid=?',(fid,))
	row = sqlCurs.fetchone()
	return row[0]

# Returns list of fileNames
def getFiles(includeFilesWithoutOption=False):
	if debug: print("getFiles: ",includeFilesWithoutOption)

	allFiles = []

	if includeFilesWithoutOption:
		for row in sqlExecute('SELECT fileName FROM files'):
			allFiles.append(row[0])

	else:
		allOpts = getOptions(['case','meta'])
		for opt in allOpts:
			optFiles = getFilesOfOption(opt)
			for f in optFiles:
				if f not in allFiles:
					allFiles.append(f)

	return allFiles

# Returns list of names of files to which the option has to be applied
def getFilesOfOption(optName):
	if debug: print("getFilesOfOption:",optName)
	oid = verifyOption(optName)

	files = []
	fids = getFidsOfOid(oid)
	if (len(fids) == 1) and (fids[0] == ''):
		return files

	for fid in fids:
		if not fid: continue
		sqlCurs.execute('SELECT fileName FROM files WHERE fid=?',(fid,))
		row = sqlCurs.fetchone()
		if (type(row[0]) != None):
			files.append(row[0])

	return files

# Returns list of cids with matching caseNames
def getMatchingCids(caseName):
	cids = []
	
	insert = ("%"+caseName.upper()+"%",)
	for c in sqlCurs.execute(
			'SELECT currentCid FROM cases \
			WHERE UPPER(caseName) LIKE ?',
			insert):
		cids.append(c[0])
	
	return cids

# Returns a list of options of given type
def getOptions(optTypes='any'):
	verifyOptionType(optTypes)
	opts = []
	for optName,optType in sqlCurs.execute('SELECT optionName,optionType FROM options'):
		if (optType in optTypes) or (optTypes == 'any'):
			opts.append(optName)

	return opts

# Returns list of options which are used in given file
def getOptionsUsedInFile(fileName):
	if debug: print('getOptionsUsedInFile: ',fileName)
	fid = verifyFile(fileName)

	usedOpts = []
	allOpts = getOptions(['case','meta'])
	for opt in allOpts:
		if isOptionUsedInFile(opt,fileName):
			usedOpts.append(opt)

	return usedOpts

# Returns cid of first case of line
def getPartriarchCid(cid):
	while getFatherCid(cid):
		cid = getFatherCid(cid)

	return cid

# Returns name of run file and directory where it is located
def getRunFileAndDir(cid,runFid):
	if debug: print('getRunFileAndDir: ',cid,runFid)

	if not runFid:
		print("No run file defined")
		sys.exit(1)

	# Get name of runfile and templateFid
	runFileName = getFileName(runFid)
	templateName = getTemplateName(runFileName)
	FQRFN = buildFQFN(cid,runFileName)
	if debug: print('getRunFileAndDir: ',FQRFN)

	# Runfile is also template file
	if (runFileName == templateName):
		runFile = FQRFN
		runDirectory = './'

	# Runfile is contained in template directory
	else:
		runFileDirs = FQRFN.split('/')
		runFile = runFileDirs.pop()
		runDirectory = '/'.join(runFileDirs)

	# Return
	return runFile,runDirectory

# Returns cids of siblings
def getSiblingsCid(cid):
	if debug: print("getSiblingsCid: ",cid)
	verifyCid(cid)

	fatherCid = getFatherCid(cid)
	if not fatherCid:
		return []

	siblings = getSonsCid(fatherCid)
	idx = siblings.index(cid)
	siblings.pop(idx)
	return siblings

# Returns cids of sons
def getSonsCid(cid):
	if debug: print("getSonsCid: ",cid)
	verifyCid(cid)

	sons = []
	for row in sqlCurs.execute(
		'''SELECT cid FROM caseData WHERE fatherCid=?''',
		(cid,)):
		sons.append(row[0])

	return sons

# Returns list of template files being directories
def getTemplateDirs():
	dirs = []
	for row in sqlCurs.execute('''
		SELECT fileName
		FROM files
		WHERE isDirectory='yes' '''):
		dirs.append(row[0])

	return dirs

# Returns fid of template directory
def getTemplateFid(fileName):
	if debug: print('getTemplateFid: ',fileName)

	# File is already known, just read template fid from DB
	fid = isFile(fileName)
	if fid:
		sqlCurs.execute('''
			SELECT templateFid
			FROM files
			WHERE fid=?''',(fid,))
		row = sqlCurs.fetchone()
		return row[0]

	# File is not known to DB, find out tmplDir
	else:
		foundIn = []
		tmplDirs = getTemplateDirs()
		for d in tmplDirs:
			if os.path.isfile(d+"/"+fileName):
				foundIn.append(d)

		l = len(foundIn)
		if (l == 0):
			print("File not contained in template directories ("+fileName+")")
			delFile(fileName,True)
			sys.exit(1)

		elif (l > 1):
			print("Warning: Found file multiple times!")
			return 0

		else:
			tDir = foundIn[0]
			tDirFid = isFile(tDir)
			return tDirFid

# Returns name of corresponding template file
def getTemplateName(fileName):
	if debug: print('getTemplateName: ',fileName)
	templateFid = getTemplateFid(fileName)

	if not templateFid:
		return fileName
	else:
		return getFileName(templateFid)

# Returns timestamp of last building time
def getTimeBuild(cid):
	verifyCid(cid)

	sqlCurs.execute('SELECT timeBuild FROM caseData WHERE cid=?',(cid,))
	row = sqlCurs.fetchone()
	return row[0]

# Returns value of meta option
def getValueOfMetaOptionOfCase(optName,caseName):
	cid = verifyCase(caseName)
	return getValueOfMetaOptionOfCid(optName,cid)

# Returns value of meta option
def getValueOfMetaOptionOfCid(optName,cid):
	verifyOption(optName,'meta')
	verifyCid(cid)

	if (optName == '_caseName'):
		return getCaseName(cid)

	if (optName == '_seriesName'):
		return getValueOfOption('seriesName')

# Returns default value of option
def getValueOfOption(optName):
	if debug: print("getValueOfOption:",optName)
	oid = verifyOption(optName)

	if isOption(optName,'meta'):
		print("Cannot handle meta options. Call getValueOfMetaOptionOf... instead.")
		sys.exit(1)

	else:
		sqlCurs.execute('SELECT defaultValue FROM options WHERE oid=?',(oid,))
		row = sqlCurs.fetchone()
		return row[0]

# Returns value of given option for specific case
def getValueOfOptionOfCase(optionName,caseName):
	cid = isCase(caseName)
	return getValueOfOptionOfCid(optionName,cid);
		
# Returns value of given option for specific cid
def getValueOfOptionOfCid(optionName,cid):
	cid = verifyCid(cid)
	oid = isOption(optionName)
	
	# Look at first if option has non-default value for case
	sqlCurs.execute('SELECT oidString,valueString FROM caseData WHERE cid=?',(cid,))
	row = sqlCurs.fetchone()

	if (row[0] != None) and (len(row[0]) > 0):
		caseOids = row[0].split(',')
		caseOids = map(int,caseOids)
		caseVals = row[1].split(',')
		caseVals = [ v.replace("_;_",",") for v in caseVals ]
		
		if oid in caseOids:
			idx = caseOids.index(oid)
			return caseVals[idx]

	# Option not set for this case, return default value
	if optionName in metaOptions:
		return getValueOfMetaOptionOfCid(optionName,cid)
	else:
		return getValueOfOption(optionName)

# Returns a cid of a youngest (leaf)
def getYoungCid(cid):
	verifyCid(cid)

	sonsCid = getSonsCid(cid)
	if (len(sonsCid) != 0):
		return getYoungCid(sonsCid[0])
	else:
		return cid

# Takes caseName and processes it according to command line arguments,
# might result in execution of multiple cases
def handleCmdCase(caseName):
	if debug: print("handleCmdCase: ",caseName)
	
	# Add case
	if isCmdLineArgument('--add','-a') \
		and not isCmdLineArgument('--option','-O'):
		addCmdCase(caseName)
	
	# Its not adding, so process
	else:
		cid = isCase(caseName)
		
		# Case with exact case name exists
		if (cid != 0):
			handleCidSingle(cid)
		
		# Look for cases containing caseName as substring
		else:
			cids = getMatchingCids(caseName)
			
			if (len(cids) == 0):
				print("No matching case ("+caseName+")")
				sys.exit(1)
			
			elif (len(cids) == 1):
				print("Did not find "+caseName+", taking "+getCaseName(cids[0]))
				handleCidSingle(cids[0])
			
			else:
				handleCidMulti(cids)

# Process single case according to command line arguments
def handleCidSingle(cid):
	if debug: print("handleCidSingle: ",cid)
	
	# Add something
	if isCmdLineArgument('--add','-a'):
		
		# Add option to cid
		if isCmdLineArgument('--option','-O') \
			and isCmdLineArgument('--value','-V'):
			addOptionToCid(
				getCmdLineArgument('--option','-O'),
				getCmdLineArgument('--value','-V'),
				cid
				)
		
		# Arguments invalid, print help
		else:
			printHelpAdd()
			sys.exit(1)
	
	# Build case
	elif isCmdLineArgument('--build','-b'):
		buildCid(cid)
	
	# Clean builds
	elif isCmdLineArgument('--clean'):

		# Removes build files without questioning
		if isCmdLineArgument('--force','-f'):
			delBuildCase(cid,True)

		# Removes build files
		else:
			delBuildCase(cid)
	
	# Delete something from case or the case itself
	elif isCmdLineArgument('--delete','-d'):
		
		# Delete options having default values from case
		if isCmdLineArgument('--default'):
			delDefaultOptionsFromCid(cid)
				
		# Delete option from case (i.e., set it to default value)
		elif isCmdLineArgument('--option','-O'):
			delOptionFromCid(
				getCmdLineArgument('--option','-O'),
				cid
				)
		
		# Delete case
		else:
			# Use caseName, delCid is part of recursive deletion procedure
			caseName = getCaseName(cid)
			delCase(caseName)

	# Modify case
	elif isCmdLineArgument('--modify','-m'):
		
		# Modify option of case
		if isCmdLineArgument('--option','-O') \
			and isCmdLineArgument('--value','-V'):
			modOptionValueOfCid(
				cid,
				getCmdLineArgument('--option','-O'),
				getCmdLineArgument('--value','-V')
				)

		# Modify name of case
		elif isCmdLineArgument('--name'):
			modNameOfCid(
				cid,
				getCmdLineArgument('--name')
				)
		
		# Arguments invalid, print help
		else:
			printHelpModify()
			sys.exit(1)
	
	# Print case
	elif isCmdLineArgument('--print','-p'):
		
		# Case including default options
		if isCmdLineArgument('--default'):
			printCidOptions(cid,True)

		# Case with only non-default options
		else:
			printCidOptions(cid)
	
	# Builds case in auto mode and runs it afterwards
	elif isCmdLineArgument('--run','-r'):
		runCid(cid)
	
	# Arguments invalid, print help
	else:
		printHelp()
		sys.exit(1)

# Process all given cids according to command line arguments
def handleCidMulti(cids):
	print("Found multiple ("+str(len(cids))+") matching cases:")
	for cid in cids:
		caseName = getCaseName(cid)
		print("  "+caseName)
	
	answer = raw_input("Proceed? (Y/n): ")
	if (answer != 'Y'):
		print("Abort.")
		sys.exit(0)
	
	for cid in cids:
		caseName = getCaseName(cid)
		print("Processing "+caseName)
		handleCidSingle(cid)

# Called if a case tree is to be build and the case (directory/file) already exists
def handleTreeBuildingForExistingCase(cid,caseFile,buildFile):
	if debug: print("handleTreeBuildingForExistingCase:",cid,caseFile,buildFile)
	if not os.path.exists(caseFile):
		return

	if not os.path.isfile(buildFile):
		print("Not a valid build file ("+buildFile+")")
		print("Delete case manually.")
		sys.exit(1)

	auto = isCmdLineArgument('--auto')
	force = isCmdLineArgument('--force','-f')

	buildCid = getBuildCid(buildFile)
	caseName = getCaseName(cid)

	# Automatic mode, decide based on buildCid and cid if case needs
	# to be rebuild, or can be leaved just like it is
	if auto:
		if (buildCid == cid):
			print(caseName+' already up to date.')
			sys.exit(0)

		force = True

	# Standard, print info and ask if case is really to delete
	else:
		print(caseFile+" already exists")
		if os.path.isfile(buildFile):
			printBuildInfo(cid,buildCid)

	# Go ahead and delete
	delBuildCase(cid,force)

# Returns case id if given argument is valid case, 0 otherwise
def isCase(caseName):
	if (len(str(caseName)) == 0):
		return 0

	for c in sqlCurs.execute('SELECT caseName,currentCid FROM cases'):
		if caseName.lower() == c[0].lower():
			return c[1]

	return 0

# Returns true if given argument is valid case id
def isCid(i,hasToBeCurrentCid=False):
	i = int(i)

	if hasToBeCurrentCid:
		for row in sqlCurs.execute('SELECT currentCid FROM cases'):
			if (i == row[0]):
				return True
	else:
		for row in sqlCurs.execute('SELECT cid FROM caseData'):
			if (i == row[0]):
				return True

	return False

# Returns true if argument exists
def isCmdLineArgument(longOpt,shortOpt="none"):
	# Use global optNames variable
	for optName in optNames:
		if (optName == shortOpt) or (optName == longOpt):
			return True

	return False

# Connect to DB
def isDB(dbFile,create=False):
	if os.path.isfile(dbFile):
		return True

	if create:
		createTables()
		return True

	return False

# Returns true if given if value is the default for option optName
def isDefaultValue(optName,value):
	defValue = getValueOfOption(optName)
	
	if (isNumber(value) and isNumber(defValue) \
		and (float(value) == float(defValue))):
		return True
	elif (value == defValue):
		return True
	else:
		return False

# Returns true if file is a directory
def isDirectory(fileName):
	fid = verifyFile(fileName)
	sqlCurs.execute('SELECT isDirectory FROM files WHERE fid=?',(fid,))
	row = sqlCurs.fetchone()

	if (row[0] == 'yes'):
		return True
	else:
		return False

# Returns true if given argument is valid file id
def isFid(i):
	for ret in sqlCurs.execute('SELECT fid FROM files'):
		if (i == ret[0]):
			return 1

	return 0

# Returns file id if file exists, 0 otherwise
def isFile(f):
	for entry in sqlCurs.execute('SELECT fid,fileName FROM files'):
		if (f.lower() == entry[1].lower()):
			return entry[0]

	return 0

# Returns true if string can be cast as float
def isNumber(s):
	try:
		float(s)
		return True
	except ValueError:
		return False

# Returns true if given argument is valid option id
def isOid(i,optType='any'):
	verifyOptionType(optType)

	for row in sqlCurs.execute('SELECT oid,optionType FROM options'):
		if ((row[1] == optType) or (optType == 'any')) and \
			(i == row[0]):
			return 1

	return 0

# Returns option id if given argument is valid option, 0 otherwise
def isOption(optName,optType='any'):
	verifyOptionType(optType)

	for row in sqlCurs.execute('SELECT oid,optionName,optionType FROM options'):
		if ((row[2] == optType) or (optType == 'any')) and \
			(optName.lower() == row[1].lower()):
			return row[0]

	return 0

# Returns true if option is set for given case
def isOptionSetForCase(optName,caseName):
	cid = verifyCase(caseName)
	return isOptionSetForCid(optName,cid)

# Returns true if option is set for given case id
def isOptionSetForCid(optName,cid):
	if debug: print("isOptionSetForCid: ",optName,cid)
	verifyCid(cid)
	oid = verifyOption(optName)

	# Get current option and value string from case
	sqlCurs.execute('SELECT oidString FROM caseData WHERE cid=?',(cid,))
	row = sqlCurs.fetchone()

	# See if option is set
	if (row[0] != None) and (len(row[0]) > 0):
		caseOids = row[0].split(',')
		caseOids = map(int,caseOids)

		if oid in caseOids:
			return True

	return False

# Returns true if option is used in given file
def isOptionUsedInFile(optName,fileName):
	if debug: print("isOptionUsedInFile: ",optName,fileName)
	oid = verifyOption(optName)
	fid = verifyFile(fileName)

	sqlCurs.execute('SELECT fidString FROM options WHERE oid=?',(oid,))
	row = sqlCurs.fetchone()
	fidString = row[0]
	fids = []

	if (fidString != None):
		fids = fidString.split(',')
		fids = map(int,fids)

	if fid in fids:
		return True
	else:
		return False

# Changes the name of cid
def modNameOfCid(cid,newName):
	if (isCase(newName) > 0):
		print("Name already in use ("+newName+")")
		sys.exit(1)
	
	insert = (newName,cid)
	sqlCurs.execute('UPDATE cases SET caseName=? WHERE currentCid=?',insert)

# Changes the name of option
def modOptionName(optName,newName):
	if debug: print("modOptionName: ",optName,newName)
	oid = verifyOption(optName)

	if (len(newName) == 0):
		print("Expected option name")
		sys.exit(1)

	if isOption(newName):
		print("Option "+newName+" already exists")
		sys.exit(1)

	insert = (newName,oid)
	sqlCurs.execute('''
		UPDATE options
		SET optionName=?
		WHERE oid=?''',insert)

# Changes default value of option
def modOptionValue(optName,optValNew):
	if debug: print("modOptionValue: ",optName,optValNew)
	oid = verifyOption(optName)
	optValOld = getValueOfOption(optName)

	# Get all cids
	allCids = []
	for row in sqlCurs.execute('SELECT cid FROM caseData'):
		allCids.append(row[0])

	# Set old value as option for all cases using the default value,
	# do not create new instances for that since nothing changed for
	# those cases
	if not isOption(optName,'series'):
		for cid in allCids:
			if not isOptionSetForCid(optName,cid):
				addOptionToCid(optName,optValOld,cid,False)

	# Update value in DB
	insert = (optValNew,oid)
	sqlCurs.execute('UPDATE options SET defaultValue=? WHERE oid=?',insert)

# Changes value of option for given case
def modOptionValueOfCase(caseName,optName,optValue):
	if debug: print("modOptionValueOfCase: ",caseName,optName,optValue)
	cid = isCase(caseName)
	modOptionValueOfCid(cid,optName,optValue)

# Changes value of option for given cid
def modOptionValueOfCid(cid,optName,optValue):
	if debug: print("modOptionValueOfCid: ",cid,optName,optValue)
	
	# If option is not present yet, add it and return
	if not isOptionSetForCid(optName,cid):
		addOptionToCid(optName,optValue,cid)
		return

	cid = verifyCid(cid)
	oid = verifyOption(optName)
	
	# Get current option and value string from case
	sqlCurs.execute('SELECT oidString,valueString FROM caseData WHERE cid=?',(cid,))
	row = sqlCurs.fetchone()
	oids = row[0].split(',')
	oids = map(int,oids)
	vals = row[1].split(',')
	vals = [ v.replace("_;_",",") for v in vals ]

	# Modify option
	idx = oids.index(oid)
	vals[idx] = optValue

	# Build strings and update DB
	oidString = ",".join(str(o) for o in oids)
	valString = ",".join(str(v).replace(",","_;_") for v in vals)

	# Update DB
	newCid = addCaseData(cid)
	updateCurrentCid(cid,newCid)
	insert = (oidString,valString,newCid)
	sqlCurs.execute('UPDATE caseData SET oidString=?,valueString=? WHERE cid=?',insert)

# Prints basic infos about found build file
def printBuildInfo(cid,buildCid):
	verifyCid(cid,True)
	verifyCid(buildCid)

	timeBuild = getTimeBuild(buildCid)
	timeStr = datetime.datetime.fromtimestamp(timeBuild).strftime('%d.%m.%Y, %H:%M')

	print("Current Cid:\t"+str(cid))
	print("Build Cid:\t"+str(buildCid))
	print("Build Time:\t"+timeStr)

# Prints all defined cases
def printCases(showDefaults=False):
	caseNames = []
	for row in sqlCurs.execute('''
			SELECT caseName
			FROM cases
			ORDER BY caseName
			'''):
		caseNames.append(row[0])

	withOptions = isCmdLineArgument('--withOptions')
	for caseName in caseNames:
		print(caseName)
		if withOptions:
			printCaseOptions(caseName,showDefaults)

# Prints given case
def printCaseOptions(caseName,showDefaults=False):
	cid = isCase(caseName)
	printCidOptions(cid,showDefaults)
	
# Prints given cid
def printCidOptions(cid,showDefaults=False):
	opts,vals,files = buildOptionsForCid(cid,showDefaults)

	table = []
	for i in range(len(opts)):
		row = [opts[i],vals[i]]
		#row.append(",".join(files[i]))
		table.append(row)

	printTable(table,4)

# Prints all defined files
def printFiles():
	fileTable = []
	for ret in sqlCurs.execute('''SELECT fid,fileName FROM files'''):
		fileTable.append((str(ret[0]),ret[1]))

	printTable(fileTable)

# Prints help message
def printHelp():
	print("Help message:")
	printHelpAdd()
	printHelpDelete()
	printHelpModify()
	printHelpPrint()
	
	print("\n\t--version\tPrints current program version")
	printHelpShortOpts()
	

def printHelpAdd(offset=0):
	offset += 1
	os = '\t' * offset

	print(os+"--add")

	offset += 1
	os = '\t' * offset

	print(os+"--option= --type= --file= --value= ")
	print(os+'\tAdds option with given type, file and, sometimes optional, default value')
	print('')

	print(os+"--option= --value= --file=")
	print(os+'\tAdds option with default value and option file')
	print('')

	print(os+"--option= --value= --case=")
	print(os+'\tAdds option with value to existing case')
	print('')

	print(os+"--case= --interactive")
	print(os+'\tAdds case using interactive menu')
	print('')
	print(os+"--case= --copy=")
	print(os+'\tAdds case by copying an existing one')
	print('')
	print(os+"--case=")
	print(os+'\tAdds case with default options')
	print('')

	print(os+"--file= --option=")
	print(os+'\tAdds file where option is also set')
	print('')
	print(os+"--file=")
	print(os+'\tAdds file')
	print('')

	print(os+'--template=')
	print(os+'\tAdds template file/directory')

def printHelpDelete(offset=0):
	offset += 1
	os = '\t' * offset

	print(os+"--delete")

	offset += 1
	os = '\t' * offset

	print(os+"--option --case")
	print(os+'\tDeletes option from case (i.e., sets to default)')
	print('')
	
	print(os+"--default --case")
	print(os+'\tDeletes options with default values from case')
	print('')

	print(os+"--file --option")
	print(os+'\tDeletes file from option')
	print('')

	print(os+"--option")
	print(os+'\tDeletes option')
	print('')

	print(os+"--case")
	print(os+'\tDeletes case')

def printHelpModify(offset=0):
	offset += 1
	os = '\t' * offset

	print(os+"--modify")

	offset += 1
	os = '\t' * offset

	print(os+"--case= --name=")
	print(os+'\tModifies name of case')
	print('')

	print(os+"--case= --option= --value=")
	print(os+'\tModifies value of option for case')
	print('')

	print(os+"--option= --name=")
	print(os+'\tModifies name of option')
	print('')

	print(os+"--option= --value=")
	print(os+'\tModifies default value of option')

def printHelpPrint(offset=0):
	offset += 1
	os = '\t' * offset

	print(os+"--print")

	offset += 1
	os = '\t' * offset

	print(os+"--case=")
	print(os+'\tPrints case and its non-default options')
	print('')

	print(os+"--case= --default")
	print(os+'\tPrints case including options having default values')
	print('')

	print(os+"--cases")
	print(os+'\tPrints all cases without options')
	print('')
	
	print(os+"--cases --withOptions")
	print(os+'\tPrints all cases with options having a non-default value')
	print('')

	print(os+"--cases --withOptions --default")
	print(os+'\tPrints all cases including options having default values')
	print('')

	print(os+"--files")
	print(os+'\tPrints all files')
	print('')

	print(os+"--options")
	print(os+'\tPrints all available case and meta options')
	print('')

	print(os+"--options --series")
	print(os+'\tPrints all set series options')

def printHelpShortOpts(offset=0):
	offset += 1
	os = '\t' * offset

	print('')
	print(os+"Long and short mode of options")
	print(os+"Upper case letters require an input value")

	offset += 1
	os = '\t' * offset

	print(os+"-a --add")
	print(os+"-b --build")
	print(os+"-d --delete")
	print(os+"-f --force")
	print(os+"-h --help")
	print(os+"-i --interactive")
	print(os+"-m --modify")
	print(os+"-p --print")
	print(os+"-r --run")
	print(os+"-s --series")
	print(os+"-t --type")
	print('')
	print(os+"-V --value")
	print(os+"-C --case")
	print(os+"-F --file")
	print(os+"-O --option")
	print(os+"-T --type")
	print('')
	
# Prints all defined options
def printOptions(optType):
	if debug: print("printOptions:",optType)
	verifyOptionType(optType)

	optRows = []
	
	for row in sqlCurs.execute('''
		SELECT oid,optionName,defaultValue
		FROM options
		WHERE optionType=?
		ORDER BY optionName''',(optType,)):
		optRows.append([row[0],row[1],row[2]])

	for i in range(len(optRows)):
		optName = optRows[i][1]
		optFiles = getFilesOfOption(optName)

		if (len(optRows[i][2]) == 0): optRows[i][2] = '-'
		if (len(optFiles) == 0): optFiles = ['-']

		# Append column with filenames
		optRows[i].append(",".join(optFiles))
	
	optRows.insert(0,["OID","Name","Value","Where applied"])
	printTable(optRows)

# Prints table
def printTable(table,offset=0):
	if (len(table) < 1): return
	# Tab width and offset tab string
	offset = ' '*offset

	# Find widths in number of tabs of columns
	numCols = len(table[0])
	colWidths = [0] * numCols

	for row in table:
		for col in range(len(row)):
			if (len(str(row[col])) > colWidths[col]):
				colWidths[col] = len(str(row[col]))

	for row in table:
		rowList = []
		for col,width in zip(row,colWidths):
			rowList.append(str(col).ljust(width))
		print(offset+" | ".join(rowList))

# Resets all tables to initial state
def resetTables():
	print("resetTables() needs better implementation")

	sqlCurs.execute('DELETE FROM options WHERE optionType!=?',('series',))
	sqlCurs.execute('DELETE FROM cases')
	sqlCurs.execute('DELETE FROM caseData')
	sqlCurs.execute('DELETE FROM files')

	sqlCurs.execute('UPDATE options SET fidString="" WHERE optionName="templateFiles"')

# Builds case in auto mode, runs it afterwards
def runCase(caseName):
	if debug: print('runCase: ',caseName)
	cid = isCase(caseName)
	runCid(cid)

# Builds case in auto mode, runs it afterwards
def runCid(cid):
	if debug: print('runCid: ',cid)
	
	if not isCmdLineArgument('--force','-f'):
		print("Use of --force flag is mandatory when running cases")
		sys.exit(1)

	buildCid(cid)

	cwd = os.getcwd()
	oid = isOption('runFiles')
	runFids = getFidsOfOid(oid)
	for runFid in runFids:
		runFile,runDir = getRunFileAndDir(cid,runFid)
		if debug: print('runCase: runFile,runDir ',runFile,runDir)
		os.chdir(runDir)
		if debug: print('runCase: running ',runFile)
		os.system("./"+runFile)
		os.chdir(cwd)

# Updates time of last build and increments number of builds
def updateCaseBuildData(caseName):
	cid = verifyCase(caseName)
	builds = getCaseBuilds(caseName)
	tstamp = int(time.time())

	insert = (tstamp,builds+1,cid)
	sqlCurs.execute('''
		UPDATE caseData
		SET timeBuild=?,builds=?
		WHERE cid=?''',insert)

# Updates currend cid of case entry in table cases
def updateCurrentCid(oldCid,newCid):
	caseName = getCaseName(oldCid)

	insert = (newCid,caseName)
	sqlCurs.execute('''
		UPDATE cases
		SET currentCid=?
		WHERE caseName=?''',insert)

# Returns fid if case is in DB, exits otherwise
def verifyCase(caseName):
	cid = isCase(caseName)
	if not cid:
		print("Not a valid case ("+caseName+")")
		sys.exit(1)
	else:
		return cid

# Exits if given cid is not valid
def verifyCid(cid,isCurrentCid=False):
	cid = int(cid)
	if not isCid(cid,isCurrentCid):
		if isCurrentCid:
			print("Not a current valid case id ("+str(cid)+")")
		else:
			print("Not a valid case id ("+str(cid)+")")
		sys.exit(1)
	else:
		return cid

# Exits if given fid is not valid
def verifyFid(fid):
	fid = int(fid)
	if not isFid(fid):
		print("Not a valid file id ("+str(fid)+")")
		sys.exit(1)

# Returns fid if fileName is in DB, exits otherwise
def verifyFile(fileName):
	fid = isFile(fileName)
	if not fid:
		print("Not a valid file ("+fileName+")")
		sys.exit(1)
	else:
		return fid

# Exits if given option is not a valid meta option
def verifyMetaOption(optName):
	if optName not in metaOptions:
		print('Not a valid meta option ('+optName+')')
		sys.exit(1)

# Returns oid if option is in DB, exits otherwise
def verifyOption(optName,optType='any'):
	verifyOptionType(optType)
	oid = isOption(optName,optType)
	if not oid:
		print("Not a valid option ("+optName+")")
		sys.exit(1)
	else:
		return oid

# Exits if given type is not a valid option type
def verifyOptionType(optType):
	optTypes = ('any','case','meta','series')

	if type(optType) is str:
		if optType not in optTypes:
			print('Not a valid option type ('+optType+')')
			sys.exit(1)

	elif type(optType) is list:
		for o in optType:
			verifyOptionType(o)

	else:
		print('Not a valid option type (',optType,')')
		print('type: ',type(optType))
		sys.exit(1)

#
# Main -----------------------------------------------------------------
#

opts, args = getArgs(shortOpts,longOpts)

if (len(opts) == 0):
	printHelp()
	sys.exit(1)

optNames,optVals = zip(*opts)
sqlCurs = [None]

if isCmdLineArgument('--help','-h'):
	printHelp()
	sys.exit(0)

if isCmdLineArgument('--version'):
	print("Version "+str(version))
	sys.exit(0)

if isCmdLineArgument('--createDB'):
	createDB(getCmdLineArgument('--createDB'))
	sys.exit(0)

for f in os.listdir("./"):
    if f.endswith(".db"):
        dbFile = f

if isCmdLineArgument("--db"):
	dbFile = getCmdLineArgument("--db")

if not os.path.isfile(dbFile):
	print("Cannot find database.")
	sys.exit(1)
else:
	sqlCon = sqlite3.connect(dbFile)
	sqlCurs = sqlCon.cursor()


# Do everything related to a specific case
if isCmdLineArgument('--case','-C'):
	handleCmdCase(getCmdLineArgument('--case','-C'));


# Anything else that is not related to a specific case
# Adding something
elif isCmdLineArgument('--add','-a'):

	# Add global option of specified type
	if (isCmdLineArgument('--option','-O')) \
		and (isCmdLineArgument('--type','-t')):
		addOptionWithType(
			getCmdLineArgument('--option','-O'),
			getCmdLineArgument('--type','-t')
			)

	# Add global option of type 'case'
	elif (isCmdLineArgument('--option','-O')) \
		and (isCmdLineArgument('--value','-V')) \
		and (isCmdLineArgument('--file','-F')):
		addOption(
			getCmdLineArgument('--option','-O'),
			getCmdLineArgument('--value','-V'),
			'case',
			getCmdLineArgument('--file','-F')
			)

	# Add file to global option
	elif (isCmdLineArgument('--file','-F')) \
		and (isCmdLineArgument('--option','-O')):
		addFileToOption(
			getCmdLineArgument('--file','-F'),
			getCmdLineArgument('--option','-O')
			)

	# File
	elif isCmdLineArgument('--file','-F'):
		addFile(getCmdLineArgument('--file','-F'))

	# Template
	elif isCmdLineArgument('--template','-T'):
		addTemplate(getCmdLineArgument('--template','-T'))

	# Runfile
	elif isCmdLineArgument('--runFile'):
		addFileToOption(
			getCmdLineArgument('--runFile'),
			'runFiles'
			)

	# Unspecified
	else:
		printHelpAdd()

# Delete something
elif isCmdLineArgument('--delete','-d'):

	# Delete file from option
	if (isCmdLineArgument('--file','-F')) \
		and (isCmdLineArgument('--option','-O')):
		delFileFromOption(
			getCmdLineArgument('--option','-O'),
			getCmdLineArgument('--file','-F')
		)

	# Delete option
	elif isCmdLineArgument('--option','-O'):
		delOption(getCmdLineArgument('--option','-O'))
		
	# Unspecified
	else:
		printHelpDelete()

# Export
elif isCmdLineArgument('--export'):
	export()

# Modify something
elif isCmdLineArgument('--modify','-m'):

	# Modify name of option
	if (isCmdLineArgument('--option','-O')) \
		and isCmdLineArgument('--name'):
		modOptionName(
			getCmdLineArgument('--option','-O'),
			getCmdLineArgument('--name')
			)

	# Modify value of option
	elif (isCmdLineArgument('--option','-O')) \
		and (isCmdLineArgument('--value','-V')):
		modOptionValue(
			getCmdLineArgument('--option','-O'),
			getCmdLineArgument('--value','-V')
			)

	# Unspecified
	else:
		printHelpModify()

# Print something
elif isCmdLineArgument('--print','-p'):

	# Cases including default options
	if isCmdLineArgument('--cases') and isCmdLineArgument('--default'):
		printCases(True)

	# Cases
	elif isCmdLineArgument('--cases'): printCases()

	# All files
	elif isCmdLineArgument('--files'): printFiles()

	# Print series options
	elif isCmdLineArgument('--options') \
	and isCmdLineArgument('--series','-s'):
		printOptions('series')

	# Print case and meta options
	elif isCmdLineArgument('--options'):
		print('Meta options')
		printOptions('meta')
		print('')
		print('Regular options')
		printOptions('case')

	# Unspecified
	else:
		printHelpPrint()

# Reset DB to initial state
elif isCmdLineArgument('--reset'):
	resetTables()

# Options incorrect
else:
	printHelp()
	sys.exit(1)

sqlCon.commit()
sqlCon.close()
sys.exit(0)
