#!/usr/bin/env python
# encoding: utf-8
"""
CacherBrowser.py

Copyright (c) 2009 jasuca.com. All rights reserved.

This class try to implement a browser that read files from Internet and return as 
string the website.
The browser caches the files and connect over various proxies to camouflate the IP
( Depending on the proxy service ).
The configuration parameters are:
	ProxyThreadController.MAX_NUMBER_THREADS (default = 3): Number of simultaneus 
		proxies to connect so download a website
	CacherBrowser.PROXY_NUMBER (default = 10): Number of proxy addresses passed 
		to the  ProxyThreadController to start downloading. Make random sublist of
		your total list. None means that pass all the proxy list
	CacherBrowser.CACHE_SIZE (default = 200): Numer of entries in the cache.
	CacherBrowser.COOKIEFILE (default = 'cookies.lwp'): File where are stored the cookies
	CacherBrowser.COOKIES (default = False): Enable to use a cookies file and automatic handle cookies
	CacherBrowser.SOCKET_TIMEOUT (default = 5): Timeout for all connections
	CacherBrowser.MAX_NUMBER_GLOBAL_THREADS (default = 275): Max number of threads open. Wait 0.5 s 
		while the others close

How to use with an example:
	#Initialize the browser
	cb = CacherBrowser()
	
	#Read the proxies
	path ="./proxyList/proxy01.txt"
	cb.readProxy(path)
	
	#Open the websites
	cb.open("http://www.google.com")
	cb.open("http://www.yahoo.com")
	
	#Print the sate of the browser
	print cb

Note: the proxy list is a ip:port for line
"""

import sys
import os
import unittest

import httplib
import cookielib            
import urllib2
import socket

import time
import threading

import random
import copy

class ProxyThread(threading.Thread):
	"""
	This class is a thread that use a specific proxy in order to make serveral browsers at the same time. It use cookies also.
	You can update the headers of the browser changing the self.headers.
	"""
	def __init__ ( self, url, proxy, ProxyThreadController, cookie = None):
		"""Initialize the clase with a url and a proxy to use and a cookie to add in the header"""
		threading.Thread.__init__(self)
		
		self.url = url
		self.proxy = proxy
		
		self.headers =  {'User-agent' : 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}          # fake a user agent, some websites (like google) don't like automated exploration
		self.txdata = None # if we were making a POST type request, we could encode a dictionary of values here - using urllib.urlencode
		
		
		#Pointer to look the browser and update the html
		self.proxyController = ProxyThreadController
		
		self.cookie = cookie
	
	def run(self):
		"""Start with the thread. Conects to a proxy and ask for the url. In case it work writes the result in self.proxyController.html"""
		#Create the proxy string
		proxy = ":".join([self.proxy[0],str(self.proxy[1])])
		####print "Using proxy: ", proxy
		
		normalExit = False
		errorCode = False
		
		try:
			
			#print "REQ", self.url, self.txdata, self.headers, "***"
			req = urllib2.Request(self.url, self.txdata, self.headers)
			req.set_proxy(proxy, 'http') #set proxy
			#insert the cookie here
			if self.cookie != None:
				req.add_header('Cookie', self.cookie)
				#print "Proxy",proxy,"using cookie", self.cookie
			
			handle = urllib2.urlopen(req) # and open it to return a handle on the url
		except Exception, e: #IOError, e:
			#pass
			print 'We failed to open "%s".' % self.url, e
			
			if hasattr(e, 'code'):
				print 'Proxy', proxy,'failed with error code - ', e.code
				errorCode = True
		else:
			#Verify no one have connected before
			if not self.__testHtmlDownloaded():
				try:
					
					infoData = handle.info()
					totalData = handle.read()
					
					normalExit = True
				except Exception, e:
					print 'Proxy', proxy,'failed with timeout'
					normalExit = False
			else:
				####print "Data obtained from an other thread"
				pass
		#Saving the data...
		if normalExit:
			self.__saveInformation(totalData, infoData)
		elif errorCode and e.code==404:
			self.__saveInformation("", "Error code 404")
			
		self.__removeFormThreadList()			
		####print "I kill myself and I erase from the list: ", self.proxy
	
	def __removeFormThreadList(self):
		"""Removes himself from the thread list in self.proxyController"""
		self.proxyController.threadsLock.acquire()
		if self in self.proxyController.threads:
			self.proxyController.threads.remove(self)
		self.proxyController.threadsLock.release()
	
	def __testHtmlDownloaded(self):
		"""Check if some other thread finished before and obtained the correct data. Used not to ask twice the same info"""
		self.proxyController.htmlLock.acquire()
		returnValue = self.proxyController.htmlDonwloaded
		self.proxyController.htmlLock.release()
		return returnValue
	
	def __saveInformation(self, totalData, infoData):
		"""Save the information in the self.proxyController.html as an string"""
		#lock MISBrowser variables
		self.proxyController.htmlLock.acquire()
		
		if not self.proxyController.htmlDonwloaded:
			#Modify the data+htmlDownloaded
			####print "Writing the html data...", self.proxy
			self.proxyController.html = totalData
			self.proxyController.info = infoData
			self.proxyController.htmlDonwloaded = True
			
			print "Proxy ", self.proxy, "obtained the information from ", [self.url]
		else:
			####print "Someone else write before me: ", self.proxy
			pass
		#unlock CacheBrowser variables
		self.proxyController.htmlLock.release()
	

class ProxyThreadController(object):
	"""This class open a website using various threads that use a proxy. In case someone finish it make a BeautifulSoup object to navigate over the net"""
	MAX_NUMBER_THREADS = 3
	
	def __init__(self, url, proxyList, cookieList=None):
		"""
		Initialize with all needed. And start downloading the website. Use a list of proxies
		and a list of cookies, if each proxy you want to use a diferent cookie (idea of ID in the cookie)
		"""
		self.html = ""
		self.info = ""
		self.htmlDonwloaded = False
		self.htmlLock = threading.Lock()
		
		self.threadsLock = threading.Lock()
		self.threads = []
		
		self.proxyList = proxyList
		self.cookieList = cookieList
		
		
		self.open(url)
		
		pass
	
	def open(self, url):
		"""Start threading with all proxies. The first process finish the function and save the information in self.html"""
		
		for proxy in self.proxyList:
			if not self.htmlDonwloaded:
				#Max num connections?
				while self.MAX_NUMBER_THREADS<=len(self.threads):
					#print "LOT OF THREADS. WAITING SOMEONE TO CLOSE"
					time.sleep(1)
				
				#We can open new connections
				print "CREATING A NEW THREAD USING PROXY: ", proxy,
				#Take a cookie from the list
				if self.cookieList != None:
					pos = random.randrange( len(self.cookieList) )
					cookie = self.cookieList[pos]
					print "AND COOKIE:", cookie
				else:
					cookie = None
					print
					
				#Open a thread with proxy and the url
				while threading.activeCount()>CacherBrowser.MAX_NUMBER_GLOBAL_THREADS:
					time.sleep(1)
					print "Lot of threads hardware", threading.activeCount()
				try:
					currentProxy = ProxyThread(url, proxy, self, cookie)
					currentProxy.start()
					self.threads.append(currentProxy)
				except Exception, e:
					print "**************** PROBLEM with a thread", e,
					print threading.activeCount()
				
				
			
			else:
				####print "WEBSITE DOWNLOAD"
				break
		
		####print "WAITING PROXIES TO RESPONDE ..."
		#While one of the threads doesn't finish
		while (not self.htmlDonwloaded) and (len(self.threads) > 0):
			time.sleep(1)
	
	def __del__(self):
		self.killAllProcess()
		pass
	
	def killAllProcess(self):
		"""Wait that all process finish the connection with the actual url"""
		####print "WAITING PROXIES TO CLOSE ..."
		# wait for all threads to finish, closing connections
		#we send a close connection and they will decide what to do
		for s in self.threads:
			####print "WAITING TO CLOSE THE THREAD WITH PROXY: ", s.proxy
			if s.isAlive() :
				s.join()
				####print "CLOSED THREAD WITH PROXY: ", s.proxy
	
	def viewingHtml(self):
		"""Shows if the html is abaiable"""
		return self.htmlDonwloaded
	
	def getHtml(self):
		"""Return the html string"""
		return self.html
	
	def getInfo(self):
		"""Return the info string"""
		return self.info
	

class CacherBrowser:
	"""
	Is a browser. Is a Singletion class, like this it's useful to reload and manage websites
	"""
	PROXY_NUMBER = 10
	CACHE_SIZE = 200
	COOKIEFILE = 'cookies.lwp'# the path and filename that you want to use to save your cookies in
	COOKIES = False #enable cookies
	SOCKET_TIMEOUT = 5 #in seconds
	MAX_NUMBER_GLOBAL_THREADS = 1500 #275
	INTERVAL_PROXY = 10 #in seconds
	
	# storage for the instance reference
	__instance = None
	
	class __impl:
		# this class stores the html and other information
		class CacheValue:
			"""This class stores the information with the html and times visited and other important info"""
			def __init__(self):
				"""This initialize the values of the class"""
				self.html = ""
				self.info = ""
				self.timer = None
				self.haveHtml = False
				
				pass
			
			def updateHtml(self, html, info):
				"""update the html and restart the timer"""
				self.html = html
				self.info = info
				self.timer = 0
				self.haveHtml = True
				pass
			
			def getHtml(self):
				"""Add one to the timer and returns the html"""
				self.timer =+ 1
				return self.html
			
			def getInfo(self):
				"""Returns the info"""
				return self.info
			
			def haveLessVisits(self, other):
				"""
				Return true if self have less visits.
				None is like infinite visites
				"""
				if self.timer == None:
					return False
				elif other.timer == None:
					return True
				else:
					return self.timer<other.timer
			
			def __str__(self):
				"""Print the CacheValue in a fancy way"""
				numberChars = 10
				html = self.html[0:numberChars]+"..."
				return "\t".join([str(self.timer), str(self.haveHtml), str(html)])
			
		
		""" Implementation of the CacherBrowser interface """
		def __init__(self):
			self.PROXY_LIST = []
			self.PROXY_NUMBER = CacherBrowser.PROXY_NUMBER
			self.CACHE_FILE = {}
			self.CACHE_SIZE = CacherBrowser.CACHE_SIZE
			self.COOKIEFILE = CacherBrowser.COOKIEFILE
			self.COOKIES = CacherBrowser.COOKIES
			self.SOCKET_TIMEOUT = CacherBrowser.SOCKET_TIMEOUT
			self.INTERVAL_PROXY = CacherBrowser.INTERVAL_PROXY
			
			self.__configureUrllib2()
			
			self.CACHE_FILE_lock = threading.Lock()
			self.PROXY_LIST_lock = threading.Lock()
			pass
		
		def __configureUrllib2(self):
			"""
			Configure the urllib2 to use the cookies file and the socket timeout
			"""
			#For the cookies - now inserted manually or via file
			if self.COOKIES:
				cj = None
				ClientCookie = None
				
				cj = cookielib.LWPCookieJar()       # This is a subclass of FileCookieJar that has useful load and save methods
				
				
				
				if cj != None:                                  # now we have to install our CookieJar so that it is used as the default CookieProcessor in the default opener handler
					if os.path.isfile(self.COOKIEFILE):
						cj.load(self.COOKIEFILE)
					
					print cj
					
					#Generate the opener
					opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
					#Install as default opener
					urllib2.install_opener(opener)
			
				
			#timeout in seconds
			socket.setdefaulttimeout(self.SOCKET_TIMEOUT)
		
		def open(self, url, cookies):
			"""returns the string with the html and the header. See if it's cached"""
			
			#Controles if it have in cache
			if self.cachedSite(url):
				return self.getInfo(url), self.getHTML(url)
			else:
				return self.forceOpen(url, cookies)
			pass
		
		def forceOpen(self, url, cookies):
			"""Like an open but refresh the cache file"""
			
			pc = ProxyThreadController(url,self.getRandomProxyList(self.PROXY_NUMBER), cookies)
			
			#Try as times as you obtain the html
			#Do not do it if PROXY_NUMBER = len(PROXY_LIST) -> not random prosibilities
			while not pc.viewingHtml():
				print "TRYING ANOTHER TIME TO GET URL:", [url]
				pc = ProxyThreadController(url,self.getRandomProxyList(self.PROXY_NUMBER), cookies)
			
			if pc.viewingHtml():
				html = pc.getHtml()
				info = pc.getInfo()
				self.pushHTML(url, html, info)
			else:
				#Maybe the list of random proxies was not ok, so repeat
				raise Exception("Problem getting HTML")
			
			return info, html
		
		def getRandomProxyList(self, numberServers=None):
			"""
			Make a random list with the proxies. If numberServers = None, make a random list with all the elements in the list/2+1
			Return the new list
			"""
			
			
			self.PROXY_LIST_lock.acquire()
			
			
			#Copy only those with the correct timespam
			now = int(time.time())
			not_used_proxies = []
			
			while len(not_used_proxies)==0:	
				for proxy in self.PROXY_LIST:
					since_when = time.time() - proxy[2]
					#print "Since whern", since_when, now, proxy[2]
					if since_when>self.INTERVAL_PROXY:
						#long not used
						not_used_proxies.append(proxy)
				
				#print "*****LEN",len(not_used_proxies)
				
				if len(not_used_proxies)==0:
					print self.INTERVAL_PROXY
					sleeping_time = self.INTERVAL_PROXY*2*(random.random()+1)
					print "SLEEPING %0.2f seconds, PROXIES OVERUSED"%(sleeping_time)
					time.sleep(sleeping_time)
					print "WAKED UP %0.2d seconds, PROXIES OVERUSED"%(sleeping_time)
			
			#start with the sublist
			len_proxyList = len(not_used_proxies)/2+1
			len_proxyList = min(len(not_used_proxies),len_proxyList)
			
			if numberServers == None:
				numberServers = len_proxyList
			if numberServers > len(not_used_proxies):
					numberServers = len_proxyList
					
			#Make the random subset
			copyProxyList = []
			copyProxyList = random.sample(not_used_proxies, numberServers)
			
			
			#make the list as used now
			for proxy in self.PROXY_LIST:
				if proxy in copyProxyList:
					proxy[2]=now
			self.PROXY_LIST_lock.release()
			
			time.sleep(1)
			
			return copyProxyList
		
		def getHTML(self, url):
			"""Return the html if it's in cache file"""
			return self.CACHE_FILE[url].getHtml()
		
		def getInfo(self, url):
			"""Return the info if it's in cache file"""
			return self.CACHE_FILE[url].getInfo()	
		
		def pushHTML(self, url, html, info):
			"""Put he html in the cache file. In it's no place remove the less used"""
			self.CACHE_FILE_lock.acquire()
			
			if self.cachedSite(url):
				self.CACHE_FILE[url].updateHtml(html, info)
			else:
				#Control the size
				if len(self.CACHE_FILE)>=self.CACHE_SIZE:
					self.removeEntry()
				self.CACHE_FILE[url] = self.CacheValue()
				self.CACHE_FILE[url].updateHtml(html, info)
				
			self.CACHE_FILE_lock.release()
		
		def removeEntry(self):
			"""Remove the less visited entry"""
			lessValue = self.CacheValue()
			
			lessValueUrl = ""
			for url, cv in self.CACHE_FILE.iteritems():
				if cv.haveLessVisits(lessValue):
					lessValueUrl = url
			#Remove lessValue
			del self.CACHE_FILE[lessValueUrl]
		
		def cachedSite(self, url):
			"""Return the cached entry"""
			return self.CACHE_FILE.has_key(url)
		
		def __str__(self):
			"""Print the information of the cache"""
			proxy = "Proxy list:\n"+str(self.PROXY_LIST)
			cacheInfo = []
			for url, cv in self.CACHE_FILE.iteritems():
				
				line = "\t".join([url, str(cv)])
				cacheInfo.append(line)
			return "\n".join([proxy, str(self.CACHE_SIZE), "\n".join(cacheInfo)])
		
		def readProxy(self, path):
			"""Read the proxy file and stores in PROXY_LIST"""
			proxyList = []
			f = open(path, 'r')
			for line in f:
				proxy, port = line.split(":")
				port = int(port)
				proxyList.append([proxy, port, 0]) #0 is to initialize a timespam 0
			self.PROXY_LIST = proxyList
			f.close()
			pass
		
	
	def __init__(self):
		""" Create singleton instance """
		# Check whether we already have an instance
		if CacherBrowser.__instance is None:
			# Create and remember instance
			CacherBrowser.__instance = CacherBrowser.__impl()
		
		# Store instance reference as the only member in the handle
		self.__dict__['_CacherBrowser__instance'] = CacherBrowser.__instance
	
	def __getattr__(self, attr):
		""" Delegate access to implementation """
		return getattr(self.__instance, attr)
	
	def __setattr__(self, attr, value):
		""" Delegate access to implementation """
		return setattr(self.__instance, attr, value)
	
	def getProxyList(self):
		"""Returns the proxy list"""
		return self.__instance.PROXY_LIST
	

##Testing
class MISBrTests(unittest.TestCase):
	
	def _testingIpAdress(self):
		"""Try to test to open a file"""
		#CacherBrowser.COOKIES = True
				
		cb = CacherBrowser()
		
		path ="./proxyList.txt"
		cb.readProxy(path)
		
		#url = "http://www.mi-ip.es/ip.php"
		url = 'http://www.ioerror.us/ip/'
		#url = 'http://www.ioerror.us/ip/headers'
		#url = 'http://www.my-proxy.com/list/proxy.php'
		
		cookies = ["GSP=ID=285d1cacd9150765:IN=b8acc395c41ea61f:CF=4"]
		pc = ProxyThreadController(url,cb.getProxyList(),cookies)
		
		if pc.viewingHtml():
			print pc.getInfo()
			print pc.getHtml()
		else:
			print "Problem with html"
		pass
	
	def _testUTFUrls(self):
		#for UTF URLS
		import urllib
		import urlparse
		def url_fix(s, charset='utf-8'):

			"""Implemented in Werkzeug
			Sometimes you get an URL by a user that just isn't a real
			URL because it contains unsafe characters like ' ' and so on.  This
			function can fix some of the problems in a similar way browsers
			handle data entered by the user:

			>>> url_fix(u'http://de.wikipedia.org/wiki/Elf (Begriffsklärung)')
			'http://de.wikipedia.org/wiki/Elf%20%28Begriffskl%C3%A4rung%29'

			:param charset: The target charset for the URL if the url was
			                given as unicode string.
			"""
			if isinstance(s, unicode):
				s = s.encode(charset, 'ignore')
			scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
			path = urllib.quote(path, '/%')
			qs = urllib.quote_plus(qs, ':&=')
			return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))
			
		cb = CacherBrowser()
		
		path ="./proxyList.txt"
		cb.readProxy(path)
		
		url = "http://www.google.ch/search?q=falç"
		
		url = url_fix(url)

		cookies = None
		pc = ProxyThreadController(url,cb.getProxyList(),cookies)
		
		if pc.viewingHtml():
			print pc.getInfo()
			print [pc.getHtml()]
		else:
			print "Problem with html"
		pass
		
		
	def _testingReadProxyFile(self):
		"""docstring for testingReadProxyFile"""
		cb = CacherBrowser()
		path ="./proxyList.txt"
		
		cb.readProxy(path)
		print "Original List"
		print cb.getProxyList()
		
		print "Random List"
		for x in range(1000):
			print cb.getRandomProxyList(1)
		
		print "Random List"
		print cb.getRandomProxyList(2)
		pass
	
	def _testingCacherBrowser(self):
		"""@todo: better test; may have problems"""
		cb = CacherBrowser()
		cb.pushHTML("hola", "htmlskjskjusosgsuyiefjsdhkkhfksjhkdjf")
		cb.pushHTML("holsa", "htmlskjss")
		cb.pushHTML("holsa", "mssss")
		
		print cb
		print cb.cachedSite("hola")
		cb.getHTML("holsa")
		cb.removeEntry()
		
		print cb.cachedSite("hola")
		
		print cb
	
	def _testingCacherBrowserWithOpen(self):
		"""Test if it caches the URL or not"""
		
		#ProxyThreadController.MAX_NUMBER_THREADS = 1
		cb = CacherBrowser()
		
		path ="./proxyList.txt"
		cb.readProxy(path)
		
		cb.open("http://www.google.com", None)

		cb.open("http://www.google.com", None)
		cb.open("http://www.yahoo.com", None)
		
		cb.open("http://www.yahoo.com", None)
		cb.open("http://www.yahoo.com", None)
		cb.open("http://www.yahoo.com", None)
		
		cb.open("http://www.aa.com", None)
		
		cb.open("http://www.cool.com", None)
		
		
		print cb
		pass
	
	def _testingSingleton(self):
		"""Testing the singleton"""
		cb = CacherBrowser()
		path ="./proxyList.txt"
		cb.readProxy(path)
		
		cb2 =  CacherBrowser()
		print cb
		print cb2
		
		pass
	
if __name__ == '__main__':
	unittest.main()