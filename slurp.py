#!/bin/python

from burp import IBurpExtender, IContextMenuFactory
from java.util import List, ArrayList
from javax.swing import JMenuItem
import urllib2
import urllib
from HTMLParser import HTMLParser
import threading
import copy

# Change Me
OUTPUT_FILE = "/home/user/Documents/SeleniumTest.html"

class HTMLFormParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.forms = []
        self.inputs = {}

    def handle_starttag(self, tag, attrs):
        if tag == 'input':
            tagID = ''
            tagName = ''
            for attr in attrs:
                if 'id' == attr[0]:
                    tagID = attr[1]
                elif 'name' == attr[0]:
                    tagName = attr[1]

            if tagID != '' and tagName != '':
                self.inputs[tagName] = tagID

        if tag == 'form':
            for attr in attrs:
                if 'id' == attr[0]:
                    self.forms.append(attr[1])


class BurpExtender(IBurpExtender, IContextMenuFactory):
    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        self.context = None

        callbacks.setExtensionName("Slurp")
        callbacks.registerContextMenuFactory(self)
        print "Go generate some selenium tests!"

        return

    def createMenuItems(self, contextMenu):
        self.context = contextMenu
        menuList = ArrayList()
        menuList.add(JMenuItem("Generate Selenium File",
                               actionPerformed=self.analyzeRequests))
        return menuList

    def analyzeRequests(self, event):
        httpRequestResponses = self.context.getSelectedMessages()

        for httpReqResp in httpRequestResponses:
            request = self._helpers.bytesToString(httpReqResp.getRequest())
            threading.Thread(target=self.generateSeleniumTest,
                             args=(httpReqResp, request)).start()

    def getResponseData(self, httpReqResp):
        responseDict = {}
        parser = HTMLFormParser()

        host = str(httpReqResp.getHttpService().getHost())
        port = int(httpReqResp.getHttpService().getPort())
        request = str(self._helpers.bytesToString(httpReqResp.getRequest()))
        headers = self._helpers.analyzeRequest(
            None, httpReqResp.getRequest()).getHeaders()
        newHeaders = copy.copy(headers)

        parts = []
        referer = ''
        newRefererStr = ''
        for header in headers:

            if 'HTTP/1.1' in header:
                parts = header.split()

            if 'Referer' in header:
                referer = header.split("Referer: ")[-1]
                responseDict['url'] = referer
                arr = referer.split("/")
                newRefererStr = ''
                for i in arr[3:]:
                    newRefererStr += "/" + str(i)

        firstLine = headers[0]
        newHeaders[0] = firstLine.replace(str(parts[1]), newRefererStr)

        newHeadersStr = "\r\n".join(newHeaders)
        oldHeadersStr = "\r\n".join(headers)

        request = request.replace(oldHeadersStr, newHeadersStr)
        request = request.replace("POST", "GET")

        response = self._callbacks.makeHttpRequest(
            host, port, True, request).tostring()

        try:
            parser.feed(response)

            flagSet = False
            for i in parser.forms:
                if 'log' in i:
                    responseDict['FormID'] = i
                    flagSet = True

            if not flagSet:
                responseDict['FormID'] = parser.forms[-1]
            responseDict['inputs'] = parser.inputs

        except:
            pass

        return responseDict

    def generateSeleniumTest(self, httpReqResp, request):
        data = self.getResponseData(httpReqResp)
        url = data['url']
        params = self._helpers.analyzeRequest(httpReqResp).getParameters()

        template = '<?xml version="1.0" encoding="UTF-8"?>\n' \
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n' \
            '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">\n' \
            '<head profile="http://selenium-ide.openqa.org/profiles/test-case">\n' \
            '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />\n' \
            '<link rel="selenium.base" href="{}" />\n' \
            '<title>Selenium Generator</title>\n' \
            '</head>\n' \
            '<body>\n' \
            '<table> cellpadding="1" cellspacing="1" border="1">\n' \
            '<thead>\n' \
            '<tr><td rowspan="1" colspan="3">Selenium Generated</td></tr>\n' \
            '</thead><tbody>\n' \
            '<tr>\n' \
            '\t<td>open</td>\n' \
            '\t<td>{}</td>\n' \
            '\t<td></td>\n' \
            '</tr>\n'.format(url, url)

        for param in params:
            if param.getType() != 2:
                try:
                    name = urllib.unquote(str(param.getName())).decode('utf8')
                    value = urllib.unquote(
                        str(param.getValue())).decode('utf8')
                    if name in data['inputs'].keys():
                        template += '<tr>\n' \
                            '\t<td>type</td>\n' \
                            '\t<td>id={}</td>\n' \
                            '\t<td>{}</td>\n' \
                            '</tr>\n'.format(name, value)
                except:
                    pass

        formID = data['FormID']

        template += '<tr>\n' \
            '\t<td>runScript</td>\n' \
            '\t<td>javascript:{{document.getElementById("{0}").submit()}}</td>\n' \
            '\t<td></td>\n' \
            '</tr>\n'\
            '</tbody></table>\n' \
            '</body>\n' \
            '</html>'.format(formID)

        f = open(OUTPUT_FILE, 'w')
        f.write(template)
        f.close()
        print "Wrote to %s" % OUTPUT_FILE
