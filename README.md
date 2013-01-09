PySocrataClient
===============

Asynchronous Tornado client to Socrata data sources.

A single instance of this class is meant for a single table from a
socrata data source, as specified by the constructor's host and view_id
parameters.

The instance is used to build the row condition and call the query_rows
function on, which asynchronously calls socrata.
	
Follows Socrata API v1.0, detailed here:
http://dev.socrata.com/deprecated/querying-datasets

Example:
	See the init function at the bottom of socrataclient.py 
	for a simple example.
	
Requirements:
	Tornado >= version 2.4 (http://www.tornadoweb.org/_
	Toro (https://github.com/ajdavis/toro)
	
Future work: 
	adapt this client to API v2.0 (http://dev.socrata.com/docs/queries)