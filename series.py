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
dbFile = "series.db"
tmplFile = "template"
buildString = "build"
debug = False

shortOpts = "abdfhimprst:v:C:F:O:T:"
longOpts = [
			"add","all","auto","build","case=",
			"cases","clean","copy=","createDB=","db=",
			"default","delete","export","help","file=","files",
			"force","withOptions","interactive",
			"name=","modify","option=",
			"options","print","reset","run","runFile=","series",
			"template=","type=","value="
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
		updateCurrentCid(caseName,newCid)
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

		if isCmdLineArgument(opts,'--file','-F'):
			fileName = getCmdLineArgument(opts,'--file','-F')
		else:
			fileName = 'none'

		addOption(optName,'',optType,fileName)


	# Adding a series option
	elif (optType == 'series'):
		if optName not in seriesOptions:
			print('Not a valid meta option ('+optName+')')
			sys.exit(1)

		# See if value is given
		if isCmdLineArgument(opt,'--value','-v'):
			value = getCmdLineArgument(opt,'--value','-v')
		else:
			value = ''

		# See if file is given
		if isCmdLineArgument(opt,'--file','-F'):
			fileName = getCmdLineArgument(opt,'--file','-F')
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
def applyOptionsToFile(caseName,fileName):
	if debug: print("applyOptionsToFile:",caseName,fileName)
	cid = verifyCase(caseName)
	fid = verifyFile(fileName)

	# Build fully qualified name of file
	FQFN = buildFQFN(caseName,fileName)

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
			adaptedLine,optsInLine = applyOptionsToString(caseName,usedOpts,line)

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
def applyOptionsToString(caseName,optsUsedInFile,inputString):
	adaptedString = inputString
	appliedOpts = []

	for opt in optsUsedInFile:

		# If option is found in line
		optStr = 'OPT_'+opt.upper()
		if (adaptedString.find(optStr) != -1):

			# Replace option string by its value
			if isOption(opt,'meta'):
				value = getValueOfMetaOption(opt,caseName)
			else:
				value = getValueOfOptionOfCase(opt,caseName)
			adaptedString = adaptedString.replace(optStr,value)

			# Keep track which options you found in this file
			if opt not in appliedOpts:
				appliedOpts.append(opt)

	# Treat caseName as special option
	adaptedString = adaptedString.replace('OPT_CASENAME','OPT_'+caseName.upper())

	return adaptedString,appliedOpts

# Makes copy of template and applies options
def buildCase(caseName):
	if debug: print("buildCase:",caseName)
	cid = verifyCase(caseName)

	# Copy template files
	buildCaseTree(caseName)

	# Get files where options are to be applied
	# File names are not case adapted yet
	optionFiles = getFiles()
	if debug: print("buildCase: optionFiles, ",optionFiles)

	# Go through all files and gather options to set in that file
	for fileName in optionFiles:
		applyOptionsToFile(caseName,fileName)

	# Update case entry for last build
	updateCaseBuildData(caseName)

# Creates case tree by copying templates
def buildCaseTree(caseName):
	if debug: print("buildCaseTree:",caseName)
	cid = verifyCase(caseName)

	tmplFiles = getFilesOfOption('templateFiles')

	# Create case files from template files, preserving symlinks
	for tFile in tmplFiles:
		cFile = buildFQFN(caseName,tFile)
		bFile = getBuildFile(cFile,tFile)

		# If file is already present
		if os.path.exists(cFile):
			handleExistingCase(cid,cFile,bFile)

		# Copy template data to create new case
		if os.path.isdir(tFile):
			#shutil.copytree(tFile,cFile,symlinks=True)		# Preserves symlinks
			shutil.copytree(tFile,cFile)
		else:
			shutil.copy(tFile,cFile)

		# Write build file
		with open(bFile,'w') as f:
			f.write(str(cid))

# Assembles fully qualified file name of file for given case name,
# i.e. the relative path regarding the script execution directory
def buildFQFN(caseName,fileName):
	if debug: print("buildFQFN:",caseName,fileName)
	fid = verifyFile(fileName)

	# Find out template fid
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
	fullCaseName = seriesName + '-' + caseName

	return FQFN.replace(tmplString,fullCaseName)

# Returns options, their values and files for given case
# If includeDefaults=True also options with default values are returned
def buildOptionsForCase(caseName,includeDefaults=False):
	cid = verifyCase(caseName)

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
		if includeDefaults or isOptionSetForCase(opt,caseName):
			optVals.append(getValueOfOptionOfCase(opt,caseName))
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
def delBuildCase(caseName,force=False):
	if debug: print("delBuildCase:",caseName)
	cid = verifyCase(caseName)

	if not force:
		print("Warning: You are about to delete build of case "+caseName+"!")
		answer = raw_input("Proceed? (Y/n): ")
		if (answer != 'Y'):
			print("Abort.")
			sys.exit(0)

	tmplFiles = getFilesOfOption('templateFiles')

	for tFile in tmplFiles:
		cFile = buildFQFN(caseName,tFile)
		bFile = getBuildFile(cFile,tFile)
		
		if os.path.isdir(cFile):
			shutil.rmtree(cFile)
		elif os.path.isfile(cFile):
			os.remove(cFile)
		else:
			print('WARNING, file could not be deleted.')
			print('May be due to mixed upper/lower case')

		if os.path.isfile(bFile):
			os.remove(bFile)

# Deletes given case and all fathers
def delCase(caseName,force=False):
	if debug: print("delCase:",caseName,force)

	if isCmdLineArgument(opts,'--force'):
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
		updateCurrentCid(caseName,newCid)
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
	print('series -m -O templateString -v '+templateString)

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
			print('series -a -C '+case+' -O '+o+" -v \'"+v+"\'")

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
				print('series -a -t '+optType+' -O '+optName+" -v \'"+optVal+"\' -F "+fName)
			else:
				print('series -a -t '+optType+' -O '+optName+' -F '+fName)

			for of in optFiles:
				print('series -a -O '+optName+' -F '+of)

		else:
			fName = optFiles.pop()
			print('series -a -O '+optName+" -v \'"+optVal+"\' -F "+fName)
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
def getCmdLineArgument(opts,longOpt,shortOpt="none"):
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
def  getRunFileAndDir(caseName,runFid):
	if debug: print('getRunFileAndDir: ',caseName,runFid)

	cid = verifyCase(caseName)
	verifyFid(runFid)

	if not runFid:
		print("No run file defined for case "+caseName)
		sys.exit(1)

	# Get name of runfile and templateFid
	runFileName = getFileName(runFid)
	templateName = getTemplateName(runFileName)
	FQRFN = buildFQFN(caseName,runFileName)
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
def getValueOfMetaOption(optName,caseName):
	verifyOption(optName,'meta')

	if (optName == '_caseName'):
		return caseName

	if (optName == '_seriesName'):
		return getValueOfOption('seriesName')

# Returns default value of option
def getValueOfOption(optName):
	if debug: print("getValueOfOption:",optName)
	oid = verifyOption(optName)

	if isOption(optName,'meta'):
		print("Cannot handle meta options. Call getValueOfMetaOption instead.")
		sys.exit(1)

	else:
		sqlCurs.execute('SELECT defaultValue FROM options WHERE oid=?',(oid,))
		row = sqlCurs.fetchone()
		return row[0]

# Returns value of given option for specific case
def getValueOfOptionOfCase(optionName,caseName):
	cid = isCase(caseName)
	if not cid:
		print('Not a valid case ('+caseName+')')
		sys.exit(1)

	oid = isOption(optionName)
	if not oid:
		print('Not a valid option ('+optionName+')')
		sys.exit(1)

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
		return getValueOfMetaOption(optionName,caseName)
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

# Handles existing case file
def handleExistingCase(cid,caseFile,buildFile):
	if debug: print("handleExistingCase:",cid,caseFile,buildFile)
	if not os.path.exists(caseFile):
		return

	if not os.path.isfile(buildFile):
		print("Not a valid build file ("+buildFile+")")
		print("Delete case manually.")
		sys.exit(1)

	auto = isCmdLineArgument(opts,'--auto')
	force = isCmdLineArgument(opts,'--force','-f')

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
	delBuildCase(caseName,force)

# Returns case id if given argument is valid case, 0 otherwise
def isCase(isC):
	if (len(str(isC)) == 0):
		return 0

	for c in sqlCurs.execute('SELECT caseName,currentCid FROM cases'):
		if isC.lower() == c[0].lower():
			return c[1]

	return 0

# Returns true if given argument is valid case id
def isCid(i,isCurrentCid=False):
	i = int(i)

	if isCurrentCid:
		for row in sqlCurs.execute('SELECT currentCid FROM cases'):
			if (i == row[0]):
				return True
	else:
		for row in sqlCurs.execute('SELECT cid FROM caseData'):
			if (i == row[0]):
				return True

	return False

# Returns true if argument exists
def isCmdLineArgument(opts,longOpt,shortOpt="none"):
	for opt,val in opts:
		if (opt == shortOpt) or (opt == longOpt):
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

# Changes the name of case
def modCaseName(caseName,newName):
	addCaseByCopy(newName,caseName)
	delCase(caseName,True)

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
	cid = verifyCase(caseName)
	oid = verifyOption(optName)
	
	# If option is not present yet, simply add and return
	if not isOptionSetForCase(optName,caseName):
		addOptionToCase(optName,optValue,caseName)
		return

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
	updateCurrentCid(caseName,newCid)
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

	withOptions = isCmdLineArgument(opts,'--withOptions')
	for caseName in caseNames:
		print(caseName)
		if withOptions:
			printCaseOptions(caseName,showDefaults)

# Prints given case
def printCaseOptions(caseName,showDefaults=False):
	opts,vals,files = buildOptionsForCase(caseName,showDefaults)

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
	print(os+'\tDeletes option from case (i.e. sets to default)')
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
	print(os+'\tPrints all cases and their non-default options')
	print('')

	print(os+"--cases --default")
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

	drop = []
	for i in range(len(optRows)):
		optName = optRows[i][1]
		optFiles = getFilesOfOption(optName)

		if (len(optRows[i][2]) == 0): optRows[i][2] = '-'
		if (len(optFiles) == 0): optFiles = ['-']

		# Append column with filenames
		optRows[i].append(",".join(optFiles))

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
	cid = verifyCase(caseName)

	if not isCmdLineArgument(opts,'--force'):
		print("Use of --force flag is mandatory when running cases")
		sys.exit(1)

	buildCase(caseName)

	oid = isOption('runFiles')
	runFids = getFidsOfOid(oid)
	for runFid in runFids:
		runFile,runDir = getRunFileAndDir(caseName,runFid)
		if debug: print('runCase: runFile,runDir ',runFile,runDir)
		os.chdir(runDir)
		if debug: print('runCase: running ',runFile)
		os.system("./"+runFile)

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
def updateCurrentCid(caseName,newCid):
	verifyCase(caseName)
	verifyCid(newCid)

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

if ('--help' in optNames) or ('-h' in optNames):
	printHelp()
	sys.exit(0)

if ('--createDB' in optNames):
	createDB(getCmdLineArgument(opts,'--createDB'))
	sys.exit(0)

for f in os.listdir("./"):
    if f.endswith(".db"):
        dbFile = f

if isCmdLineArgument(opts,"--db"):
	dbFile = getCmdLineArgument(opts,"--db")

if not os.path.isfile(dbFile):
	print("Cannot find database.")
	sys.exit(1)
else:
	sqlCon = sqlite3.connect(dbFile)
	sqlCurs = sqlCon.cursor()



# Adding something
if ('--add' in optNames) or ('-a' in optNames):

	# Add global option of specified type
	if (('--option' in optNames) or ('-O' in optNames)) \
		and (('--type' in optNames) or ('-t' in optNames)):
		addOptionWithType(
			getCmdLineArgument(opts,'--option','-O'),
			getCmdLineArgument(opts,'--type','-t')
			)

	# Add global case option
	elif (('--option' in optNames) or ('-O' in optNames)) \
		and (('--value' in optNames) or ('-v' in optNames)) \
		and (('--file' in optNames) or ('-F' in optNames)):
		addOption(
			getCmdLineArgument(opts,'--option','-O'),
			getCmdLineArgument(opts,'--value','-v'),
			'case',
			getCmdLineArgument(opts,'--file','-F')
			)

	# Add option to case
	elif (('--option' in optNames) or ('-O' in optNames)) \
		and (('--case' in optNames) or ('-C' in optNames)) \
		and (('--value' in optNames) or ('-v' in optNames)):
		addOptionToCase(
			getCmdLineArgument(opts,'--option','-O'),
			getCmdLineArgument(opts,'--value','-v'),
			getCmdLineArgument(opts,'--case','-C')
			)

	# Add file to global option
	elif (('--file' in optNames) or ('-F' in optNames)) \
		and (('--option' in optNames) or ('-O' in optNames)):
		addFileToOption(
			getCmdLineArgument(opts,'--file','-F'),
			getCmdLineArgument(opts,'--option','-O')
			)

	# Add case by menu
	elif (('--case' in optNames) or ('-C' in optNames)) \
		and ('--interactive' in optNames) or ('-i' in optNames):
		addCaseByMenu(getCmdLineArgument(opts,'--case','-C'))

	# Add case by copy
	elif (('--case' in optNames) or ('-C' in optNames)) \
		and ('--copy') in optNames:
		addCaseByCopy(
			getCmdLineArgument(opts,'--case','-C'),
			getCmdLineArgument(opts,'--copy'),
			)

	# Add default case
	elif ('--case' in optNames) or ('-C' in optNames):
		addCase(getCmdLineArgument(opts,'--case','-C'))

	# File
	elif ('--file' in optNames) or ('-F' in optNames):
		addFile(getCmdLineArgument(opts,'--file','-F'))

	# Template
	elif ('--template' in optNames) or ('-T' in optNames):
		addTemplate(getCmdLineArgument(opts,'--template','-T'))

	# Runfile
	elif ('--runFile' in optNames):
		addRunFile(getCmdLineArgument(opts,'--runFile'))

	# Unspecified
	else:
		printHelpAdd()

# Build case
elif ('--build' in optNames) or ('-b' in optNames):

	if ('--case' in optNames) or ('-C' in optNames):
		buildCase(getCmdLineArgument(opts,'--case','-C'))

	else:
		print('Missing case')

# Clean builds
elif ('--clean' in optNames):

	# Removes build files without questioning
	if (('--case' in optNames) or ('-C' in optNames)) \
		and (('--force' in optNames) or ('-f' in optNames)):
		delBuildCase(getCmdLineArgument(opts,'--case','-C'),True)

	# Removes build files
	elif (('--case' in optNames) or ('-C' in optNames)):
		delBuildCase(getCmdLineArgument(opts,'--case','-C'))

# Delete something
elif ('--delete' in optNames) or ('-d' in optNames):

	# Delete option from case
	if (('--case' in optNames) or ('-C' in optNames)) \
		and (('--option' in optNames) or ('-O' in optNames)):
		delOptionFromCase(
			getCmdLineArgument(opts,'--option','-O'),
			getCmdLineArgument(opts,'--case','-C')
			)

	# Delete file from option
	elif (('--file' in optNames) or ('-F' in optNames)) \
		and (('--option' in optNames) or ('-O' in optNames)):
		delFileFromOption(
			getCmdLineArgument(opts,'--option','-O'),
			getCmdLineArgument(opts,'--file','-F')
		)

	# Delete option
	elif ('--option' in optNames) or ('-O' in optNames):
		delOption(getCmdLineArgument(opts,'--option','-O'))

	# Delete case
	elif ('--case' in optNames) or ('-C' in optNames):
		delCase(getCmdLineArgument(opts,'--case','-C'))

	# Unspecified
	else:
		printHelpDelete()

# Export
elif ('--export' in optNames):
	export()

# Modify something
elif ('--modify' in optNames) or ('-m' in optNames):

	# Modify option of case
	if (('--case' in optNames) or ('-C' in optNames)) \
		and (('--option' in optNames) or ('-O' in optNames)) \
		and (('--value' in optNames) or ('-v' in optNames)):
		modOptionValueOfCase(
			getCmdLineArgument(opts,'--case','-C'),
			getCmdLineArgument(opts,'--option','-O'),
			getCmdLineArgument(opts,'--value','-v')
			)

	# Modify name of case
	elif (('--case' in optNames) or ('-C' in optNames)) and \
		('--name' in optNames):
		modCaseName(
			getCmdLineArgument(opts,'--case','-C'),
			getCmdLineArgument(opts,'--name')
			)

	# Modify value of option
	elif ('--option' in optNames) or ('-O' in optNames) \
		and ('--name' in optNames):
		modOptionName(
			getCmdLineArgument(opts,'--option','-O'),
			getCmdLineArgument(opts,'--name')
			)

	# Modify value of option
	elif ('--option' in optNames) or ('-O' in optNames) \
		and (('--value' in optNames) or ('-v' in optNames)):
		modOptionValue(
			getCmdLineArgument(opts,'--option','-O'),
			getCmdLineArgument(opts,'--value','-v')
			)

	# Unspecified
	else:
		printHelpModify()

# Print something
elif ('--print' in optNames) or ('-p' in optNames):

	# Case including default options
	if (('--case' in optNames) or ('-C' in optNames)) \
		and ('--default' in optNames):
		printCaseOptions(getCmdLineArgument(opts,'--case','-C'),True)

	# Cases
	elif (('--case' in optNames) or ('-C' in optNames)):
		printCaseOptions(getCmdLineArgument(opts,'--case','-C'))

	# Cases including default options
	elif ('--cases' in optNames) and ('--default' in optNames):
		printCases(True)

	# Cases
	elif ('--cases' in optNames): printCases()

	# All files
	elif ('--files' in optNames): printFiles()

	# Print series options
	elif ('--options' in optNames) \
	and (('--series' in optNames) or ('-s' in optNames)):
		printOptions('series')

	# Print case and meta options
	elif ('--options' in optNames):
		printOptions('meta')
		printOptions('case')

	# Unspecified
	else:
		printHelpPrint()

# Reset DB to initial state
elif ('--reset' in optNames):
	resetTables()

# Builds case in auto mode and runs it afterwards
elif ('--run' in optNames):
	if (('--case' in optNames) or ('-C' in optNames)):
		runCase(getCmdLineArgument(opts,'--case','-C'))

# Sets runfile

# Options incorrect
else:
	printHelp()
	sys.exit(1)

sqlCon.commit()
sqlCon.close()
sys.exit(0)
