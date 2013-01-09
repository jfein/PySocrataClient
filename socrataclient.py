import json
import time
from tornado import httpclient, gen, ioloop
import toro


class SocrataClient:
    '''
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
    '''


    def __init__(self, host, view_id, app_token=None):
        '''
        Parameters:
            host      - The domain of the socrata data source, for example
                        "data.seattle.gov".
            
            view-id   - The view ID for the specific table 
            
            app-token - The app token to piggyback on the socrata request
        '''
        self.host = host
        self.view_id = view_id
        self.app_token = app_token
        self.lock = toro.Lock()
		
            
    # Calls socrata API asynchronously
    @gen.engine
    def _call_api(
            self,
            uri,
            callback=lambda x: x,
            method="GET",
            data=None
    ):
        '''
        Makes an asynchronous request to the socrata API of
        this client's hostname.
        
        Uses Tornado's AsyncHTTPClient
        '''
    
        # http request to socrata
        body = (json.dumps(data) if data else None)
        headers = { "Content-type" : "application/json" }
        if self.app_token:
            headers["X-App-Token"] = self.app_token            
        request = httpclient.HTTPRequest(
            "http://" + self.host + uri, 
            method=method, 
            headers=headers, 
            body=body
        )      
            
        # send request asynchronously
        http_client = httpclient.AsyncHTTPClient()
        response = yield gen.Task(http_client.fetch, request)
                        
        # Check the response
        if response.error:
            print "There was an error detected."
            print "Response status = %s.\n" % response.code
            print "Response = %s.\n" % response.body
            rawResponse = None
        else:
            rawResponse = response.body
            
        callback(json.loads(rawResponse))

            
    @gen.engine
    def _get_columns(
            self,
            callback=lambda x : x
    ):
        '''
        Returns the column information for this client's socrata table.
        Makes one request to the socrata API.
        '''
        cols = yield gen.Task(
            self._call_api,
            method="GET",
            uri="/api/views/" + self.view_id + "/columns.json"
        )
        callback(cols)
        
        
    def _get_col_id(self, name):
        '''
        Returns the ID for the column with the specified fieldName.
        '''
        for col in self.cols:
            if col["fieldName"] == name:
                return col["id"]
           
           
    def _get_col_keys(self):
        '''
        Returns the fieldName keys, in order, for each column in this table.
        '''
        return [ col['fieldName'] for col in self.cols ]
        
        
    # Run query, returns parsed & formatted data
    @gen.engine
    def query_rows(
            self, 
            condition, 
            callback=lambda x : x
    ):
        '''
        Performs a query on this client's table to return all rows
        that match the inputted condition.
        
        The while loop will continue to make requests if we use incorrect
        column IDs in the request, in which case the columns will be refreshed.
        Column refreshing is coordinate between callback chains using Toro.
        
        Each row returned is a simple dictionary with keys as the socrata 
        fieldName.
        
        Parameters:
            condition - The condition to query socrata with. Must be constructed
                        from this client instance in order to have correct 
                        column IDs.
                        
            callback -  The callback to be called with the returned rows
        '''
        
        while True:
            # Refresh columns if needed in coordinated fashion
            yield gen.Task(self.lock.acquire)
            if not getattr(self, "cols", None):
                self.cols = yield gen.Task(self._get_columns)
            self.lock.release()
            
            # eval query w/ these columns
            condition_evalled = condition()
        
            # data for the socrata API request
            data = {
                "originalViewId" : self.view_id,
                "name" : "SoClient Inline Filter",
                "columns" : self.cols,
                "query" : { "filterCondition" : condition_evalled }
            }

            # call socrata API asynchronously
            response = yield gen.Task(
                self._call_api,
                method="POST",
                uri="/api/views/INLINE/rows.json?method=index",
                data=data
            )
            
            # Used invalid columns in request, so delete cols to
            # trigger refresh on next loop iteration
            if "Cannot find column" in response.get("message", ""):
                del(self.cols)
            # Columns were OK, so no need to reload columns and redo the request
            else:
                break
            
        rows = []

        # Format data into list of simple dictionaries
        # only if valid response w/ valid data
        if response and response.get("data"):
            raw_rows = response["data"]
            keys = self._get_col_keys()
            start_key = len(raw_rows[0]) - len(keys)
            for raw_row in raw_rows:
                row = {}
                for i, key in enumerate(keys):
                    row[key] = raw_row[i + start_key]
                rows.append(row)
            
        callback(rows)

        
    '''
    Methods to generate conditional terms for querying
    '''
    
    
    def _operator(self, operator, *args):
        def func():
            vals = [ f() for f in args ]
            return {
                "type" : "operator",
                "value" : operator,
                "children" : vals
            }
        return func
        
    def AND(self, *args):
        return self._operator("AND", *args)

    def OR(self, *args):
        return self._operator("OR", *args)
         
    def EQUALS(self, *args):
        return self._operator("EQUALS", *args)
        
    def NOT_EQUALS(self, *args):
        return self._operator("NOT_EQUALS", *args)
         
    def IS_BLANK(self, *args):
        return self._operator("IS_BLANK", *args)
        
    def IS_NOT_BLANK(self, *args):
        return self._operator("IS_NOT_BLANK", *args)
        
    def STARTS_WITH(self, *args):
        return self._operator("STARTS_WITH", *args)   
        
    def CONTAINS(self, *args):
        return self._operator("CONTAINS", *args) 
        
    def NOT_CONTAINS(self, *args):
        return self._operator("NOT_CONTAINS", *args)
        
    def GREATER_THAN(self, *args):
        return self._operator("GREATER_THAN", *args)
        
    def GREATER_THAN_OR_EQUALS(self, *args):
        return self._operator("GREATER_THAN_OR_EQUALS", *args)
        
    def LESS_THAN(self, *args):
        return self._operator("LESS_THAN", *args)
        
    def LESS_THAN_OR_EQUALS(self, *args):
        return self._operator("LESS_THAN_OR_EQUALS", *args)
        
    def BETWEEN(self, *args):
        return self._operator("BETWEEN", *args)
                
    def WITHIN_CIRCLE(self, *args):
        return self._operator("WITHIN_CIRCLE", *args)
        
    def VAL(self, val):
        def func():
            return {
                "type" : "literal",
                "value" : val
            }
        return func

    def COL(self, name):
        def func():
            return { 
                "columnId" : self._get_col_id(name),
                "type" : "column"
            }
        return func
        
        
        
if __name__ == '__main__':

    @gen.engine
    def main(callback):
        # Instantiate a socrata client to
        # http://data.seattle.gov/Transportation/Street-Parking-Signs/it8u-sznv
        cl = SocrataClient("data.seattle.gov", "it8u-sznv", "fD6XiUvwNu0MpmRCIBdx4A7VI")
    
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
                
        rows = yield gen.Task(cl.query_rows, query)
        print rows
        
        callback()

    # Start the IO loop and start the asynchronous request
    loop = ioloop.IOLoop.instance()
    main(callback=loop.stop)
    loop.start()