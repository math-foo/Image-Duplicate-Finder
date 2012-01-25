#!/usr/bin/python

#    Copyright 2012, Caelyn McAulay

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import Image
import os
from shutil import copy2, move
from optparse import OptionParser

class Logger(object):
	ERROR = 0
	WARNING = 1
	INFO = 2
	DEBUG = 3

	def __init__(self, log_level):
		self.log_level = self.log_level_value(log_level)

	def log_level_value(self, log_level):
		if log_level == "error":
			return self.ERROR;
		elif log_level == "warning":
			return self.WARNING
		elif log_level == "info":
			return self.INFO
		elif log_level == "debug":
			return self.DEBUG
		else:
			#this should be handed off to the logger with a level of 'error'; but since this may have happened while we were creating the logger....
			exception_message = "Invalid input to log_level_value function: %s" % log_level
			raise Exception(exception_message)			

	def log(self, message_log_level, message):
		raise NotImplementedError("Calling the log function of AbstractLogger.")

	def close(self):
		#only needed by loggers with filehandlers
		return

class NullLogger(Logger):
	def log(self, message_log_level, message):
		#do nothing with the message, this *is* the null logger
		return

class ScreenLogger(Logger):
	def log(self, message_log_level, message):
		if self.log_level >= message_log_level:
			print message

class FileLogger(Logger):
	def __init__(self, log_level, file_name):
		self.log_level = self.log_level_value(log_level)
		self.file_handler = open(file_name,'w')

	def log(self, message_log_level, message):
		if self.log_level >= message_log_level:
			self.file_handler.write(message+'\n')


	def close(self):
		self.file_handler.close()

def image_hash(im):
	global size
	new_size = size,size

	im = im.resize(new_size)

	if im.mode != "L" and im.mode != "RGB":
		im = im.convert("RGB")
	im = im.convert("1")

	num = 0

	for i in list(im.getdata()):
		num *= 2
		if i != 0:
			num += 1

	return num



parser = OptionParser()

parser.add_option("-f", "--file", dest="input_dir_name", help="detect duplicate images in the directory INPUT_DIR_NAME")
parser.add_option("-o", "--output", dest="output_dir_name", help="move images into the directory OUTPUT_DIR_NAME, with each set of duplicated images placed in a subdirectory, and unduplicated images placed in a subdirectory called \"unduplicated\"")
parser.add_option("-s", type="int", dest="sensitivity", help="set sensitivity of matches, with higher numbers being more sensitive. NOT RECOMMENDED")
parser.add_option("-c", "--copy", action="store_true", dest="copy", help="copy the sorted images into the file specified by output instead of moving the original images. This option is ignored without an output file.")
parser.add_option("-v", action="store_true", dest="verbose", help="Turns on logging, with a default value of 'error' which maybe overridden by the --log option.")
parser.add_option("-q", action="store_false", dest="verbose", help="Turns off all logging including error messages.")
parser.add_option("--log", dest="log_level", help="Sets level of detail for log function. legal values: error (will log any errors), warning (in addition to what is logged by error, will also log warnings), info (in addition to what is logged by warning, will also log results), debug (in addition to what is logged by info, will log debugging info). Default level is info when verbose.")
parser.add_option("--logfile", dest="log_file", help="Specifies file to save log file to. Otherwise, logging is sent to standard out.")


parser.set_defaults(	input_dir_name=os.curdir,
			sensitivity=4,
			output_dir_name=os.curdir,
			copy=False,
			verbose=True,
			log_file="",
			log_level="error")

(options, args) = parser.parse_args()

input_dir_name = options.input_dir_name.strip()
output_dir_name = options.output_dir_name.strip()
size = options.sensitivity

#Normalizing case. Please don't run this in Turkish.
options.log_level = options.log_level.lower()

if options.log_level not in ["error","warning","info","debug"]:
	exception_message = "Invalid input for option --log: %s" % (options.log_level)
	raise Exception(exception_message)
	

if options.verbose:
	if options.log_file:
		logger = FileLogger(options.log_level, options.log_file)
	else:
		logger = ScreenLogger(options.log_level)
else:
	logger = NullLogger(options.log_level)

if output_dir_name != os.curdir and output_dir_name not in os.listdir(os.curdir):
	try:
		os.mkdir(output_dir_name)
	except OSError:
		logger.log(logger.ERROR, "could not create directory %s" % (output_dir_name))
		raise

try:
	files_to_open = os.listdir(input_dir_name)
except OSError:
	logger.log(logger.ERROR, "could not list directories in %s " % (input_dir_name))
	raise

cur_dict = {}
dup_dict = {}

for file_name in files_to_open:
	title = os.path.join(input_dir_name, file_name)

	try:
		logger.log(logger.DEBUG, "Attempting to open file %s" % (title))
		im = Image.open(title)
		result = image_hash(im)

		if result not in cur_dict:
			logger.log(logger.DEBUG, "%s is an unduplicated image" % (title))
			cur_dict[result] = file_name
		elif result not in dup_dict:
			logger.log(logger.DEBUG, "%s is a duplicated image" % (title))
			titles = [cur_dict[result], file_name]
			dup_dict[result] = titles
		else:
			logger.log(logger.DEBUG, "%s is a duplicated image" % (title))
			titles = dup_dict[result]
			titles.append(file_name) 
	except IOError:
		#potentially we are given a directory with non-image files or directories, in that case we want to fail gracefully like this
		logger.log(logger.DEBUG, "%s cannot be opened as an image" % (title))
		continue
	

if not cur_dict:
	if input_dir_name == os.curdir:
		logger.log(logger.WARNING, "no images found in current directory")
	else:
		logger.log(logger.WARNING, "no images in directory %s" % (input_dir_name))
elif not dup_dict:		
	if input_dir_name == os.curdir:
		logger.log(logger.INFO, "no duplicate images found in current directory")
	else:
		logger.log(logger.INFO, "no duplicate images in directory %s" % (input_dir_name))
else:
	if len(dup_dict) == 1:
		message =  "1 duplicated image found"
	else:
		message = "%i duplicated images found" % (len(dup_dict))

	if input_dir_name == os.curdir:
		logger.log(logger.INFO , "%s in current directory" % (message))
	else:
		logger.log(logger.INFO, " %s in %s" % (message, input_dir_name))

	logger.log(logger.INFO,"The following are groups of identical images:\n")

	for dup_set in dup_dict.viewvalues():
		for img_name in dup_set:
			logger.log(logger.INFO, img_name)
		logger.log(logger.INFO, "\n")			


dir_names = ['unduplicated']
unique_name_counter = 0

for result in dup_dict:
	#want to put unduplicated images together
	del cur_dict[result]

	dup_set = dup_dict[result]

	#will turn foo.jpg into foo to use a directory name	
	dir_img_name = dup_set[0].split(".")[0]

	#this is a dirty hack
	if dir_img_name in dir_names:
		dir_img_name = dir_img_name + "_" + str(unique_name_counter)
		unique_name_counter += 1

	dir_names.append(dir_img_name)		

	dst_dir_name = os.path.join(output_dir_name, dir_img_name)
	
	try:
		os.mkdir(dst_dir_name)
	except OSError:
		logger.log(logger.ERROR,"Could not create directory %s" % (dst_dir_name))
		raise
	
	for image_name in dup_set:
			src_file_name = os.path.join(input_dir_name,image_name)

			if options.copy:
				logger.log(logger.DEBUG, "Copying %s into %s" % (src_file_name, dst_dir_name))
				copy2(src_file_name, dst_dir_name)
			else:
				logger.log(logger.DEBUG, "Moving %s into %s" % (src_file_name, dst_dir_name))
				move(src_file_name, dst_dir_name)

undup_dir_name = os.path.join(output_dir_name, "unduplicated")

try:
	os.mkdir(undup_dir_name)
except OSError:
	logger.log(logger.ERROR, "Could not create directory %s" % (undup_dir_name))
	raise

for result in cur_dict:
	image_name = cur_dict[result]
	src_file_name = os.path.join(input_dir_name,image_name)	
	
	if options.copy:
		logger.log(logger.DEBUG,"Copying %s  into %s" % (src_file_name, undup_dir_name))
		copy2(src_file_name, undup_dir_name)
	else:
		logger.log(logger.DEBUG, "Moving %s into %s" % (src_file_name, undup_dir_name))
		move(src_file_name, undup_dir_name)

#closing possible log file
logger.close()		
			
