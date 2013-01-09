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
	
Requirements:
* Tornado >= version 2.4 (http://www.tornadoweb.org/)
* Toro (https://github.com/ajdavis/toro)
	
Future work: 
* Adapt this client to API v2.0 (http://dev.socrata.com/docs/queries)

Example:
```python

@tornado.gen.engine
def main(callback):
	# Instantiate a socrata client to
	# http://data.seattle.gov/Transportation/Street-Parking-Signs/it8u-sznv
	cl = SocrataClient("data.seattle.gov", "it8u-sznv", None)

	# Query to retrieve rows w/ objectid between 0 and 20
	# that contain the word "Park" in either the "customtext"
	# or "categoryde" columns.
	query = cl.AND(
			cl.GREATER_THAN(cl.COL("objectid"), cl.VAL(0)),
			cl.LESS_THAN(cl.COL("objectid"), cl.VAL(20)),
			cl.OR(
				cl.CONTAINS(cl.COL("customtext"), cl.VAL("PARK")), 
				cl.CONTAINS(cl.COL("categoryde"), cl.VAL("PARK"))
			)
		)
			
	rows = yield tornado.gen.Task(cl.query_rows, query)
	print rows
	
	callback()

# Start the IO loop and start the asynchronous request
loop = tornado.ioloop.IOLoop.instance()
main(callback=loop.stop)
loop.start()
```