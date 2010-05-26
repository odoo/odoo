import urllib

def get_absolute_file_path( url ):
	url_unquoted = urllib.unquote(url)
	return os.name == 'nt' and url_unquoted[1:] or url_unquoted 

# This function reads the content of a file and return it to the caller
def read_data_from_file( filename ):
	fp = file( filename, "rb" )
	data = fp.read()
	fp.close()
	return data

# This function writes the content to a file
def write_data_to_file( filename, data ):
	fp = file( filename, 'wb' )
	fp.write( data )
	fp.close()

