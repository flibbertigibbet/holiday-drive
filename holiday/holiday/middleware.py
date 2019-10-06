from django.db import connection
from django.utils.log import getLogger

logger = getLogger(__name__)


class QueryCountDebugMiddleware(object):
    """
    This middleware will log the number of queries run
    and the total time taken for each request (with a
    status code of 200). It does not currently support
    multi-db setups.
    """

    def process_response(self, request, response):
        # Don't print SQL queries for binary outputs!
        # if istext(response.content) == 0:
        #  print('got text response')
        #  return response

        if response.status_code == 200:
            total_time = 0
            for query in connection.queries:
                query_time = query.get('time')
                if query_time is None:
                    # django-debug-toolbar monkeypatches the connection
                    # cursor wrapper and adds extra information in each
                    # item in connection.queries. The query time is stored
                    # under the key "duration" rather than "time" and is
                    # in milliseconds, not seconds.
                    query_time = query.get('duration', 0) / 1000
                total_time += float(query_time)
            logger.debug('%s queries run, total %s seconds' %
                         (len(connection.queries), total_time))
            return response


def istext(s):
    if "" in s:
        return 0
    if not s:  # Empty files are considered text
        return 1
    # Get the non-text characters (maps a character to itself then
    # use the 'remove' option to get rid of the text characters.)
    t = s.translate(string.maketrans("", ""), "".join(
        map(chr, range(32, 127)) + list("nrtb")))
    # If more than 30% non-text characters, then
    # this is considered a binary file
    if float(len(t))/len(s) >= 0.30:
        return 0
