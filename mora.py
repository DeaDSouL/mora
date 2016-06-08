#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#---------------------------------------
# 
# App Name: MoRa, The Movies Rated Tool.
# Version : 0.1.6
# Author  : DeaDSouL (Mubarak Alrashidi)
# License : GNU GPL V3
# 
#---------------------------------------

from __future__ import print_function
import os
import sys
import argparse
from json       import loads    as json_loads,       dump as json_dump
from re         import match    as re_match
from stat       import S_ISSOCK as stat_S_ISSOCK
if sys.version_info[0] == 3:
    import pickle
    import urllib as urllib2
    from urllib.parse   import quote        as urllib_quote
    from urllib.error   import HTTPError    as urllib2_HTTPError
    from urllib.error   import URLError     as urllib2_URLError
    from urllib.request import urlopen      as urllib2_urlopen
else:
    import cPickle as pickle
    import urllib2
    from urllib     import quote        as urllib_quote
    from urllib2    import HTTPError    as urllib2_HTTPError
    from urllib2    import URLError     as urllib2_URLError
    from urllib2    import urlopen      as urllib2_urlopen


def _iteritems(dic=None):
    if sys.version_info[0] == 3: return dic.items()
    else: return dic.iteritems()



class MoRa:

    args            = ''    # the user inputs
    cwd_path        = ''    # current working directory in an absolute path format
    rel_path        = ''    # scanned relative path
    abs_path        = ''    # scanned absolute path
    found_movies    = []    # will have dictionaries as elements, that hold each movie's info
    added_movies    = []    # need this, to avoid the for loop all self.found_movies:basename
    maybe_movies    = []    # will have dictionaries as elements, that hold directory's info, that might be a movie
    ignored_dirs    = {'not_movie':[], 'by_user':[], 'outer_link':[], 'inexistent':[], 'unreadable':[]}   # will hold the ignored dirs, grouped by: 1. not_movie, 2. by_user, 3. outer_link
    app_log         = []    # will have each log as an element
    cache_path      = ''    # cache path
    cache_file      = 'cache.pkl'   # cache filename
    cache_data      = {}    # will hold all the movies rateds, to increase the result's speed
    cache_exists    = True  # whether cache file is available or not
    rated_aliases   = {}    # will be used to convert the most popular rated to our selected one. (which are listed in self.rated_types)
    rated_results   = {}    # will holds the final results of the movies info
    rated_types     = ( 'G', 'PG', 'PG-13', 'R', 'NC-17', 'UNRATED', 'UNKNOWN' )
    # Source: https://en.wikipedia.org/wiki/Video_file_format
    mov_extensions  = ('.webm', '.mkv', '.vob', '.ogv', '.ogg', '.drc', '.gifv', '.mng', '.avi', '.mov', '.qt', '.wmv', '.yuv', '.rm', '.rmvb', '.asf', '.asx', '.mp4', '.m4p', '.m4v', '.mpg', '.mp2', '.mpeg', '.mpe', '.mpv', '.m2v', '.svi', '.3gp', '.3g2', '.mxf', '.roq', '.nsv', '.flv', '.f4v', '.f4p', '.f4a', '.f4b')
    # omdb: http://www.omdbapi.com
    # tmdb: https://www.themoviedb.org/documentation/api
    # rtdb: http://developer.rottentomatoes.com/docs/read/Home
    api_list        = {'omdb':{'url':'http://www.omdbapi.com/?apikey=&t=%s&y=%s&plot=short&r=json', 'response_rated_key':'Rated', 'response_year_key':'Year', 'response_status_key':'Response', 'status_success_value':'True', 'status_fails_value':'False'}}
    # Output things
    line_100        = '-'*66
    line_33         = '-'*22
    clear_line      = ' '*100
    json_filename   = 'mora_reaults.json'

    # ------------------------------------------------------------------

    def __init__(self):
        self.initParser()
        self.initCache()
        self.loadCache()
        self.rated_results  = {rt: [] for rt in self.rated_types} # Alt to: for r in self.rated_types: self.rated_results[r] = []
        # Misc
        self.rated_aliases['NOT RATED'] = 'UNRATED'
        self.rated_aliases['NOTRATED']  = 'UNRATED'
        self.rated_aliases['UNRATED']   = 'UNRATED'
        self.rated_aliases['UNKNOWN']   = 'UNKNOWN'
        self.rated_aliases['N/A']       = 'UNKNOWN'
        self.rated_aliases['NA']        = 'UNKNOWN'
        self.rated_aliases[' ']         = 'UNKNOWN'
        self.rated_aliases['']          = 'UNKNOWN'
        # US
        self.rated_aliases['G']         = 'G'
        self.rated_aliases['PG']        = 'PG'
        self.rated_aliases['PG-13']     = 'PG-13'
        self.rated_aliases['R']         = 'R'
        self.rated_aliases['X']         = 'NC-17'
        self.rated_aliases['NC-17']     = 'NC-17'
        self.rated_aliases['TV-Y']      = 'G'
        self.rated_aliases['TV-Y7']     = 'G'
        self.rated_aliases['TV-G']      = 'G'
        self.rated_aliases['TV-PG']     = 'PG'
        self.rated_aliases['TV-14']     = 'PG-13'
        self.rated_aliases['TV-MA']     = 'R'
        # UK
        self.rated_aliases['Uc']        = 'G'
        self.rated_aliases['UC']        = 'G'
        self.rated_aliases['U']         = 'G'
        self.rated_aliases['PG']        = 'PG'      # Duplicated
        self.rated_aliases['12A']       = 'PG-13'
        self.rated_aliases['12']        = 'PG-13'
        self.rated_aliases['15']        = 'R'       # OR: PG-13
        self.rated_aliases['18']        = 'R'
        self.rated_aliases['R18']       = 'NC-17'
        # France
        self.rated_aliases['U']         = 'G'       # Duplicated
        self.rated_aliases['12']        = 'PG-13'   # Duplicated
        self.rated_aliases['16']        = 'R'
        self.rated_aliases['18']        = 'NC-17'

    # ------------------------------------------------------------------

    def main(self):
        self.validateDirs()
        self.findMovieDirs(self.rel_path)
        self.scrapMovies()
        self.saveCache()
        self.executeArgs()
        sys.exit(0)

    # ------------------------------------------------------------------

    def initParser(self):
        # TODO: needs work  -> 1) links
        parser = argparse.ArgumentParser(prog='mora', description='Get Movies Rated.')
        parser.add_argument('DIR', type=str, metavar='SCAN_DIR', nargs='?', action='store', default=os.getcwd(), help='The path of the directory to be scanned.')
        parser.add_argument('-V', '--version', action='version', version='%(prog)s\'s Version: 0.1', default=False, help='Show %(prog)s\'s version and exit.')
        parser.add_argument('-f', '--force', action='store_true', default=False, help='Rescan movies and re-get their rateds.')
        parser.add_argument('-s', '--stats', action='store_true', default=False, help='Show the statistics.')
        parser.add_argument('-d', '--debug', action='store_true', default=False, help='Show ignored directories.')
        parser.add_argument('-i', '--ignore', dest='user_ignores', metavar='DIR', nargs='*', help='Ignore one or multi directories. (ex: %(prog)s movies -i "movies/dir1" "movies/dir2/dir3"). And each provided directory should have the "scanned directory" as a prefix, for example if we want to scan videos/movies, and we want to ignore 2016/ which is in that folder, then the syntax is: (ex: %(prog)s videos/movies -i videos/movies/2016)')
        parser.add_argument('-e', '--export', metavar=self.json_filename, nargs='?', const=self.json_filename, default=None, help='Export the results to a JSON list. The default output file name is "%s" if you want to change it, just specify the name you want to use after this argument. Note that if the file already exists, a suffix of an incremental number will be added to the file name.' % self.json_filename)
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-p', '--print', dest='print_rated', action='store_true', default=False, help='Print the movies grouped by their rated.')
        group.add_argument('-l', '--links', action='store_true', default=False, help='Generate symlinks to all the scanned movies. Foldered by their rated.')
        group2 = parser.add_mutually_exclusive_group()
        group2.add_argument('-v', '--verbose', action='store_true', default=False, help='Increase output verbosity.')
        group2.add_argument('-q', '--quiet', action='store_true', default=False, help='Decrease output verbosity.')
        #subparsers = parser.add_subparsers(help='Main Commands', dest='cmd')
        #parser_scan = subparsers.add_parser('scan', help='(ex: %(prog)s scan "path/to/dir") To preform a scan of the movies Rated.')
        #parser_scan.add_argument('DIR', type=str, nargs='?', action='store', default=os.getcwd(), help='The path of the directory to scan.')
        self.args = parser.parse_args()

    # ------------------------------------------------------------------

    def validateDirs(self):
        # TODO: rewrite it, to avoid the following messy code
        if not os.path.exists(self.args.DIR): # predefined dirs to be scanned
            self.log('[ERROR]: "%s" --> The provided directory to be scanned does not exist!' % self.args.DIR, True)
            sys.exit(1)
        elif not os.access( self.args.DIR, os.R_OK ):
            self.log('[ERROR]: "%s" --> The provided directory to be scanned is unreadable!' % self.args.DIR, True)
            sys.exit(1)
        elif not os.path.isdir(self.args.DIR):
            self.log('[ERROR]: "%s" --> The provided directory to be scanned is NOT a directory!' % self.args.DIR, True)
            sys.exit(1)

        self.args.DIR = self.args.DIR.rstrip(os.path.sep)

        if self.args.user_ignores: # predefined dirs to be ignored
            # to make sure dirs don't have the trailing slashes
            self.args.user_ignores[:] = [v.rstrip(os.path.sep) for v in self.args.user_ignores]
            for i in self.args.user_ignores:
                d = {'rel_path':i, 'abs_path':os.path.abspath(i)}
                if not os.path.exists(d['abs_path']):
                    self.log('[ERROR]: "%s" --> The predefined ignored directory does not exist!' % i, True)
                    sys.exit(1)
                if not os.path.isdir(d['abs_path']):
                    self.log('[ERROR]: "%s" --> The predefined ignored directory is NOT a directory!' % i, True)
                    sys.exit(1)
                elif not os.access( d['abs_path'], os.R_OK ):
                    self.log('[ERROR]: "%s" --> The predefined ignored directory is unreadable!' % i, True)
                    sys.exit(1)
                else:
                    self.ignored_dirs['by_user'].append(d)

        self.cwd_path = os.path.abspath(os.getcwd())
        self.rel_path = self.args.DIR[:]
        self.abs_path = os.path.abspath(self.args.DIR)

        return True

    # ------------------------------------------------------------------

    def executeArgs(self):
        if self.args.print_rated: self.printRatedResults()
        if self.args.links: self.mkSymLinks()
        if self.args.stats: self.printStatistics()
        if self.args.debug: self.printDebug()
        if self.args.export: self.exportResults('normal')

    # ------------------------------------------------------------------

    def mkSymLinks(self):
        for r in self.rated_types:
            rdir = os.path.join( self.cwd_path, '_Rated_', r )
            if not os.path.isdir(rdir):
                os.makedirs(rdir)
        #for r,m in self.rated_results.iteritems():
        #    pass

    # ------------------------------------------------------------------

    def findMovieDirs(self, path=None):
        if not os.path.isdir(path) or path == None:
            self.log('Abort scanning! invalid dir: %s' % path)
            return False
        for f in os.listdir(path):
            m = {}
            m['rel_path']   = self.buildPath( (path,f) )
            m['abs_path']   = os.path.abspath( m['rel_path'] )
            m['basename']   = os.path.basename( f )
            m['title']      = ''
            m['year']       = ''
            m['rated']      = ''
            if self.args.user_ignores and m['rel_path'] in self.args.user_ignores:
                self.log('Ignoring predefined ignored directory: %s' % m['rel_path'])
                continue
            if os.path.islink( m['abs_path'] ):
                if self.abs_path not in os.path.realpath( m['abs_path'] ):
                    self.log('Ignoring link: %s' % m['abs_path'] )
                    continue
            if not os.path.exists( m['abs_path'] ):
                self.log('Ignoring Inexistent: %s' % m['abs_path'] )
            elif not os.access( m['abs_path'], os.R_OK ):
                self.log('Ignoring Unreadable: %s' % m['abs_path'] )
            elif stat_S_ISSOCK(os.stat(m['abs_path']).st_mode):
                self.log('Ignoring Socket: %s' % m['abs_path'] )
            elif os.path.isfile( m['abs_path'] ):
                self.log('Ignoring File: %s' % m['abs_path'] )
            elif os.path.isdir( m['abs_path'] ):
                match = re_match(r'(.*) \((\d{4})\)', m['basename'])        # by: cyphase
                #match = re_match(r'^([^(]+) \((\d+)\)$', m['basename'])    # by: Francisco
                if match:
                    m['title'] = match.groups()[0]
                    m['year'] = match.groups()[1]
                    self.addMovie(m)
                else:
                    if not self.isMovie(m):
                        self.log('Confirmed not a movie: %s' % m['rel_path'])
                        self.ignored_dirs['not_movie'].append(m)
                    else:
                        self.log('Might be a movie: %s' % m['rel_path'])
                        self.maybe_movies.append(m)
                    self.findMovieDirs( m['rel_path'] )
            else:
                self.log('Ignoring Unknown type: %s' % ff)
        return True

    # ------------------------------------------------------------------

    # TODO: reWork on it, since it will be called to check dirs only not files!
    def isMovie(self, d=None):
        if type(d) != dict:
            return False
        if os.path.isfile(d['abs_path']):
            e = os.path.splitext(d['abs_path'])[1]
            return True if e.lower() in self.mov_extensions else False
        elif os.path.isdir(d['abs_path']):
            for f in os.listdir(d['rel_path']):
                # check only files & links, since dirs will be scanned by findMovieDirs()
                f_abs = os.path.abspath(f)
                if os.path.islink(f):
                    f_real = os.path.realpath(f_abs)
                    if self.abs_path not in f_real:
                        self.log('Ignoring link: %s' % f )
                        return False
                    else:
                        print(' f old: %s' % f)
                        f = os.path.relpath(f_real, os.path.join(self.cwd, self.rel_path))
                        print('f_real: %s' % f_real)
                        print(' f new: %s' % f)
                        #if os.path.isfile(f_real):
                        #       e = os.path.splitext(f_real)[1]
                        #       if e.lower() in self.mov_extensions: return True
                if os.path.isfile(f):
                    e = os.path.splitext(f)[1]
                    if e.lower() in self.mov_extensions: return True
        return False

    # ------------------------------------------------------------------

    def scrapMovies(self):
        if self.args.verbose: print(self.line_100)
        total_movies = len(self.found_movies)
        if total_movies < 1: self.log('Did not found any movie!')
        else:
            i = 0
            for m in self.found_movies:
                i += 1
                self.rePrint('Processing: (%d/%d) %s' % (i, total_movies, m['basename']))
                m['rated'] = 'UNKNOWN'
                self.getRated(m)
            self.rePrint()

    # ------------------------------------------------------------------

    def getRated(self, movie='', useYear=True):
        if type(movie) != dict: return False
        if not self.args.force and movie['basename'] in self.cache_data:
            dataRated = self.cache_data[movie['basename']].upper()
            if dataRated not in self.rated_aliases: # if it is unrecognized Rated
                return self.apiRequest(movie, useYear)
            movie['rated'] = dataRated
            if not self.args.quiet:
                self.rePrint('Cache:%s%s ---> %s' % ((10-len(movie['rated']))*' ', movie['rated'], movie['basename']), False)
            self.rated_results[self.rated_aliases[movie['rated']]].append(movie)
            return True
        else:
            return self.apiRequest(movie, useYear)

    # ------------------------------------------------------------------

    # url, response_rated_key, response_year_key, response_status_key, status_success_value, status_fails_value
    def apiRequest(self, movie='', useYear=True):
        if type(movie) != dict: return False
        if sys.version_info[0] == 3: title, year, gotError = urllib_quote(movie['title'].encode('utf8')), urllib_quote(movie['year'].encode('utf8')) if useYear else '', False # py3
        else: title, year, gotError = urllib_quote(movie['title']).encode('utf8'), urllib_quote(movie['year']).encode('utf8') if useYear else '', False #py2
        for api_name, api in _iteritems(self.api_list):
            try:
                if sys.version_info[0] == 3: data = json_loads( urllib2_urlopen(api['url'] % (title, year)).read().decode('utf-8') ) # py3
                else: data = json_loads( urllib2_urlopen(api['url'] % (title, year)).read() ) # py2
                if api['response_status_key'] in data and data[api['response_status_key']] == api['status_success_value']:
                    dataRated = data[api['response_rated_key']].upper() if api['response_rated_key'] in data else 'UNKNOWN'
                    if dataRated not in self.rated_aliases:
                        self.log('Unrecognized Rated: "%s" - API: "%s" - Movie: "%s" - Year: "%s"' % (dataRated, api_name, title, year))
                        self.rated_aliases[dataRated] = 'UNKNOWN'
                    movie['rated'] = dataRated
            except (urllib2_HTTPError, urllib2_URLError) as e:
                gotError = True
                #print('\r%s' % self.clear_line),
                self.rePrint()
                #print('\r%s' % self.clear_line, end='')
                self.log('\rError occurred while checking the rated for "%s"' % movie['basename'])
            if self.rated_aliases[movie['rated']] != 'UNKNOWN':
                break # Found the Rated, so let's exit the loop
        if not self.args.quiet and not gotError:
            self.rePrint('Live :%s%s ---> %s' % ((10-len(movie['rated']))*' ', movie['rated'], movie['basename']), False)
        self.rated_results[self.rated_aliases[movie['rated']]].append(movie)
        return True

    # ------------------------------------------------------------------

    def addMovie(self, movie=None):
        if type(movie) != dict or 'basename' not in movie:
            return False
        if movie['basename'] not in self.added_movies:
            self.log('Found a movie: %s' % movie['rel_path'])
            self.found_movies.append(movie)
            self.added_movies.append(movie['basename'])
            return True
        else:
            self.log('Ignoring duplicated movie: %s' % movie['rel_path'])
            return False

    # ------------------------------------------------------------------

    def buildPath(self, dirs=None):
        if type(dirs) == tuple or type(dirs) == list:
            ret = ''
            for d in dirs:
                ret = os.path.join(ret, d)
            return ret
        else:
            return False

    # ------------------------------------------------------------------

    def log(self, text=None, forcePrint=False):
        if text == None: return False
        if self.args.verbose or forcePrint: print(text)
        self.app_log.append(text)
        return True
    # ------------------------------------------------------------------

    def rePrint(self, msg='', putComma=True):
        print('\r%s' % self.clear_line, end=''),
        #if not msg: return False
        if putComma: print('\r%s' % msg, end=''),
        else: print('\r%s' % msg)
        sys.stdout.flush()

    # ------------------------------------------------------------------

    def printRatedResults(self):
        print(self.line_100)
        print('RATED Movies (%d)' % len(self.found_movies))
        i = 0
        for r in self.rated_results:
            i += 1
            print('|__ %s (%d)' % (r, len(self.rated_results[r])))
            for m in self.rated_results[r]:
                lvl1_tree = '|' if i < len(self.rated_results) else ' '
                print('%s   |__ %s - [%s]' % (lvl1_tree, m['basename'], m['rated']))


    # ------------------------------------------------------------------

    def printStatistics(self):
        print(self.line_100)
        print('      Total G: %d' % len(self.rated_results['G']))
        print('     Total PG: %d' % len(self.rated_results['PG']))
        print('  Total PG-13: %d' % len(self.rated_results['PG-13']))
        print('      Total R: %d' % len(self.rated_results['R']))
        print('  Total NC-17: %d' % len(self.rated_results['NC-17']))
        print('Total UNRATED: %d' % len(self.rated_results['UNRATED']))
        print('Total UNKNOWN: %d' % len(self.rated_results['UNKNOWN']))
        print(self.line_33)
        print(' Total Movies: %d' % len(self.found_movies))
        print(' Ignored Dirs: %d' % (len(self.ignored_dirs['not_movie'])+len(self.ignored_dirs['by_user'])+len(self.ignored_dirs['outer_link'])))
        print(' Maybe Movies: %d' % len(self.maybe_movies))
        print(self.line_100)
        print('     CWD Path: %s' % self.cwd_path)
        print('Relative Path: %s' % self.rel_path)
        print('Absolute Path: %s' % self.abs_path)

    # ------------------------------------------------------------------

    def printDebug(self):
        print(self.line_100)
        total_ignores = sum(len(self.ignored_dirs[l]) for l in self.ignored_dirs)
        print('Ignored Dirs (%d):' % total_ignores)
        i = 0
        for t in self.ignored_dirs:
            i += 1
            print('|__ %s (%d)' % (t, len(self.ignored_dirs[t])))
            for m in self.ignored_dirs[t]:
                lvl1_tree = '|' if i < len(self.ignored_dirs) else ' '
                print('%s   |__ %s' % (lvl1_tree, m['rel_path']))
        print(self.line_33)
        print('Maybe Movies:')
        for m in self.maybe_movies:
            print('    %s' % m['basename'])
        print(self.line_100)
        pass

    # ------------------------------------------------------------------

    def exportResults(self, kind='normal'):
        i = 0
        name, ext = os.path.splitext(self.args.export)
        while os.path.exists(self.args.export):
            i += 1
            self.args.export = '%s_%d%s' % (name, i, ext)

        if kind == 'full':
            ret = self.rated_results
        else:
            #ret = {k:[{kk:dd[kk] for kk in ['basename', 'rated']} for dd in self.rated_results[k]] for k in self.rated_results}
            ret = {rt: {} for rt in self.rated_results}
            for r,l in _iteritems(self.rated_results):
                for m in l:
                    ret[r][m['basename']] = m['rated']

        with open(self.args.export, 'w') as outFile:
            json_dump(ret, outFile)

    # ------------------------------------------------------------------

    def initCache(self):
        self.cache_path = os.path.join( os.path.expanduser('~'), '.local', 'share', 'mora' )
        if os.path.exists( self.cache_path ) and not os.path.isdir( self.cache_path ):
            self.cache_exists = False
            self.log('ERROR: Won\'t be using cache. because "%s" is file not a directory' % self.cache_path)
            return False
        elif not os.path.exists( self.cache_path ):
            os.makedirs( self.cache_path )
            self.cache_exists = True
            self.log('Creating cache directory: %s' % self.cache_path)
        return True

    # ------------------------------------------------------------------

    def saveCache(self):
        if not self.cache_exists:
            return False
        for r,l in _iteritems(self.rated_results):
            #if r not in ('UNRATED', 'UNKNOWN'):
            if r != 'UNKNOWN':
                for m in l:
                    self.cache_data[m['basename']] = m['rated']
        cacheFile = os.path.join(self.cache_path, self.cache_file)
        pickle.dump( self.cache_data, open(cacheFile, 'wb'), protocol=2 )
        return True

    # ------------------------------------------------------------------

    def loadCache(self):
        cacheFile = os.path.join(self.cache_path, self.cache_file)
        if not self.cache_exists or not os.path.isfile(cacheFile):
            return False
        self.cache_data = pickle.load( open(cacheFile, 'rb') )
        return True

    # ------------------------------------------------------------------


    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    #   THE FOLLOWING DEFS ARE JUST FOR TESTING, AND SHOULD BE DELETED
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------


    # ------------------------------------------------------------------

    def __devPrintList(self, l=None):
        if type(l) != list: return False
        for m in l:
            for k,v in _iteritems(m):
                print('%s ---> %s' % (k,v))
            print(self.line_100)

    # ------------------------------------------------------------------



    # ------------------------------------------------------------------



    # ------------------------------------------------------------------



    # ------------------------------------------------------------------





if __name__ == '__main__':
    try:
        MoRa().main()
    except KeyboardInterrupt as e:
        pass
