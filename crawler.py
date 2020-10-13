import urllib.request as req
import sys
import os
from html.parser import HTMLParser
import socketserver
import http.server
import socket
import threading

connections = []


class FIFO_Policy:
    def __init__(self, seedURLs):
        self.initialSeedURLs = seedURLs
        self.queue = list(seedURLs)

    def getURL(self, c, iteration):
        if len(self.queue) == 0:
            self.queue = list(self.initialSeedURLs)
        return self.queue.pop(0)

    def updateURLs(self, c, retrievedURLs, retrievedURLsWD, iteration):
        temp = list()
        for url in retrievedURLs:
            temp.append(url)
        temp.sort(key=lambda url: url[len(url) - url[::-1].index('/'):])

        for url in temp:
            self.queue.append(url)


class Container:
    def __init__(self):
        self.country = 'spain'
        # The name of the crawler"
        self.crawlerName = "Tianming"
        # Example ID
        self.example = "exercise2"
        # Root (host) page
        self.rootPage = "https://www.gov.pl"
        self.pageURLPrefix = "https://www.gov.pl/web/koronawirus/wiadomosci?page="
        # Initial links to visit
        self.seedURLs = ["https://www.gov.pl/web/koronawirus/wiadomosci?page=1"]
        # Maintained URLs
        self.URLs = set([])
        # Outgoing URLs (from -> list of outgoing links)
        self.outgoingURLs = {}
        # Incoming URLs (to <- from; set of incoming links)
        self.incomingURLs = {}
        # Class which maintains a queue of urls to visit.
        self.generatePolicy = FIFO_Policy(self.seedURLs)
        # Page (URL) to be fetched next
        self.toFetch = None
        # Number of iterations of a crawler.
        self.iterations = 1

        # If true: store all crawled html pages in the provided directory.
        self.storePages = True
        self.storedPagesPath = "./" + self.example + "/pages/"
        # If true: store all discovered URLs (string) in the provided directory
        self.storeURLs = True
        self.storedURLsPath = "/" + self.example + "/urls/"
        # If true: store all discovered links (dictionary of sets: from->set to),
        # for web topology analysis, in the provided directory
        self.storeOutgoingURLs = True
        self.storedOutgoingURLs = "/" + self.example + "/outgoing/"
        # Analogously to outgoing
        self.storeIncomingURLs = True
        self.storedIncomingURLs = "/" + self.example + "/incoming/"
        self.pageNumber = 1
        self.maxPageNumber = 2

        # If True: debug
        self.debug = True


class Parser(HTMLParser):
    def __init__(self, c):
        HTMLParser.__init__(self)
        self.output_list = []
        self.output_titles = []
        self.currentLink = ""
        self.reachedSectionStart = False
        self.reachedItemStart = False
        self.reachedTitleStart = False
        self.depth = 0
        self.container = c

    def handle_starttag(self, tag, attrs):
        if self.reachedItemStart:
            if tag == 'div':
                if dict(attrs).get('class') == 'title':
                    self.reachedTitleStart = True

        if self.reachedSectionStart:
            if tag == 'a':
                self.currentLink = dict(attrs).get('href')
                self.reachedItemStart = True

        if tag == 'div':
            if dict(attrs).get('class') == 'art-prev art-prev--near-menu':
                self.reachedSectionStart = True
            else:
                self.depth += 1

    def handle_data(self, data):
        if self.reachedTitleStart:
            self.output_list.append((self.container.rootPage + self.currentLink))
            self.output_titles.append(data)

    def handle_endtag(self, tag):
        if tag == 'div':
            self.reachedTitleStart = False
            if self.depth == 0:
                self.reachedSectionStart = False
            else:
                self.depth -= 1
        if tag == 'a':
            self.reachedItemStart = False


def inject(c):
    for l in c.seedURLs:
        if c.debug:
            print("Injecting " + str(l))
        c.URLs.add(l)


def generate(c, iteration):
    url = c.pageURLPrefix + str(iteration + 1)
    # url = c.generatePolicy.getURL(c, iteration)
    # if url == None:
    #     if c.debug:
    #         print("   Fetch: error")
    #     c.toFetch = None
    #     return None
    # WITH NO DEBUG!
    print("   Next page to be fetched = " + str(url))
    c.toFetch = url


def fetch(c):
    URL = c.toFetch
    if c.debug:
        print("   Downloading " + str(URL))
    try:
        opener = req.build_opener()
        opener.addheadders = [('User-Agent', c.crawlerName)]
        webPage = opener.open(URL)

        return webPage
    except:
        return None


def removeWrongURL(c):
    c.URLs.remove(c.toFetch)


def parse(c, page, iteration):
    # data to be saved (DONE)
    htmlData = page.read()
    # obtained URLs (TODO)
    p = Parser(c)
    p.feed(str(htmlData))
    # retrievedURLs = set(p.output_list)
    # retrievedTitles = set(p.output_titles)
    retrievedURLs = p.output_list
    retrievedTitles = p.output_titles
    if c.debug:
        print("   Extracted " + str(len(retrievedURLs)) + " links")
    # p.output_list.clear()

    return retrievedURLs, retrievedTitles


# -------------------------------------------------------------------------
# Normalise newly obtained links (TODO)
def getNormalisedURLs(retrievedURLs):
    result = set()
    for url in retrievedURLs:
        result.add(url.lower())
    return result


# -------------------------------------------------------------------------
# Remove duplicates (duplicates) (TODO)
def removeDuplicates(c, retrievedURLs):
    retrievedURLs = retrievedURLs - c.URLs
    return retrievedURLs


# -------------------------------------------------------------------------
# Filter out some URLs (TODO)
def getFilteredURLs(c, retrievedURLs):
    toLeft = set([url for url in retrievedURLs if url.lower().startswith(c.rootPage)
                  and url != c.toFetch])
    if c.debug:
        print("   Filtered out " + str(len(retrievedURLs) - len(toLeft)) + " urls")
    return toLeft


# -------------------------------------------------------------------------
# Store HTML pages (DONE)
def storePage(c, htmlData):
    relBeginIndex = len(c.rootPage)
    # totalPath = "./" + c.example + "/pages/" + c.toFetch[relBeginIndex + 1:]
    totalPath = "./" + c.example + "/pages/links.txt"

    if c.debug:
        print("   Saving HTML page " + totalPath + "...")

    totalDir = os.path.dirname(totalPath)

    if not os.path.exists(totalDir):
        os.makedirs(totalDir)

    with open(totalPath, "wb+") as f:
        f.write(htmlData)
        f.close()


# -------------------------------------------------------------------------
# Store URLs (DONE)
def storeURLs(c):
    relBeginIndex = len(c.rootPage)
    totalPath = "./" + c.example + "/urls/urls.txt"

    if c.debug:
        print("Saving URLs " + totalPath + "...")

    totalDir = os.path.dirname(totalPath)

    if not os.path.exists(totalDir):
        os.makedirs(totalDir)

    data = [url for url in c.URLs]
    data.sort()

    with open(totalPath, "w+") as f:
        for line in data:
            f.write(line + "\n")
        f.close()


# -------------------------------------------------------------------------
# Update outgoing links (DONE)
def updateOutgoingURLs(c, retrievedURLsWD):
    if c.toFetch not in c.outgoingURLs:
        c.outgoingURLs[c.toFetch] = set([])
    for url in retrievedURLsWD:
        c.outgoingURLs[c.toFetch].add(url)


# -------------------------------------------------------------------------
# Update incoming links (DONE)
def updateIncomingURLs(c, retrievedURLsWD):
    for url in retrievedURLsWD:
        if url not in c.incomingURLs:
            c.incomingURLs[url] = set([])
        c.incomingURLs[url].add(c.toFetch)


# -------------------------------------------------------------------------
# Store outgoing URLs (DONE)
def storeOutgoingURLs(c):
    relBeginIndex = len(c.rootPage)
    totalPath = "./" + c.example + "links.txt"

    if c.debug:
        print("Saving URLs " + totalPath + "...")

    totalDir = os.path.dirname(totalPath)

    if not os.path.exists(totalDir):
        os.makedirs(totalDir)

    data = [url for url in c.outgoingURLs]
    data.sort()

    with open(totalPath, "w+") as f:
        for line in data:
            s = list(c.outgoingURLs[line])
            s.sort()
            for l in s:
                f.write(line + " " + l + "\n")
        f.close()


# -------------------------------------------------------------------------
# Store incoming URLs (DONE)
def storeIncomingURLs(c):
    relBeginIndex = len(c.rootPage)
    totalPath = "./" + c.example + "/incoming_urls/incoming_urls.txt"

    if c.debug:
        print("Saving URLs " + totalPath + "...")

    totalDir = os.path.dirname(totalPath)

    if not os.path.exists(totalDir):
        os.makedirs(totalDir)

    data = [url for url in c.incomingURLs]
    data.sort()

    with open(totalPath, "w+") as f:
        for line in data:
            s = list(c.incomingURLs[line])
            s.sort()
            for l in s:
                f.write(line + " " + l + "\n")
        f.close()


    # Iterate...
    # for iteration in range(c.iterations):
    #
    #     if c.debug:
    #         print("=====================================================")
    #         print("Iteration = " + str(iteration + 1))
    #         print("=====================================================")
    #     # Prepare a next page to be fetched
    #     generate(c, iteration)
    #     if (c.toFetch == None):
    #         if c.debug:
    #             print("   No page to fetch!")
    #         continue
    #
    # Generate: it downloads html page under "toFetch URL"
    #     page = fetch(c)
    #
    #     if page == None:
    #         if c.debug:
    #             print("   Unexpected error; skipping this page")
    #         removeWrongURL(c)
    #         continue
    #
    # Parse file
    #     htmlData, retrievedURLs = parse(c, page, iteration)
    #
    # Store pages
    #     if c.storePages:
    #         storePage(c, htmlData)
    #
    ### normalise retrievedURLs
    #     retrievedURLs = getNormalisedURLs(retrievedURLs)
    #
    ### update outgoing/incoming links
    #     updateOutgoingURLs(c, retrievedURLs)
    #    updateIncomingURLs(c, retrievedURLs)

    ### Filter out some URLs
    #     retrievedURLs = getFilteredURLs(c, retrievedURLs)
    #
    ### removeDuplicates
    #     retrievedURLsWD = removeDuplicates(c, retrievedURLs)
    #
    ### update urls
    #     c.generatePolicy.updateURLs(c, retrievedURLs, retrievedURLsWD, iteration)
    #
    # Add newly obtained URLs to the container
    #     if c.debug:
    #         print("   Maintained URLs...")
    #         for url in c.URLs:
    #             print("      " + str(url))
    #
    #     if c.debug:
    #         print("   Newly obtained URLs (duplicates with maintaines URLs possible) ...")
    #         for url in retrievedURLs:
    #             print("      " + str(url))
    #     if c.debug:
    #         print("   Newly obtained URLs (without duplicates) ...")
    #         for url in retrievedURLsWD:
    #             print("      " + str(url))
    #         for url in retrievedURLsWD:
    #             c.URLs.add(url)

    # store urls
    # if c.storeURLs:
    #     storeURLs(c)
    # if c.storeOutgoingURLs:
    #     storeOutgoingURLs(c)
    # if c.storeIncomingURLs:
    #     storeIncomingURLs(c)


def getLinks(container, maxIterations):
    # Inject: parse seed links into the base of maintained URLs
    inject(container)

    # Iterate...
    for iteration in range(maxIterations):

        if container.debug:
            print("=====================================================")
            print("Iteration = " + str(iteration + 1))
            print("=====================================================")
        # Prepare a next page to be fetched
        generate(container, iteration)
        if (container.toFetch == None):
            if container.debug:
                print("   No page to fetch!")
            continue

        # Generate: it downloads html page under "toFetch URL"
        page = fetch(container)

        if page == None:
            if container.debug:
                print("   Unexpected error; skipping this page")
            removeWrongURL(container)
            continue

        retrievedURLs, retrievedTitles = parse(container, page, iteration)
        return retrievedURLs, retrievedTitles


def handler(c, a, container, maxIter):
    global connections
    while True:
        data = c.recv(1024)
        link, title = getLinks(container, maxIter)
        for i in range(len(link)):
            c.send(bytes(title[i] + "€€€" + link[i] + "\n", 'utf-8'))
        if not data:
            connections.remove(c)
            c.close()
            break


def main():
    # Initialise data
    container = Container()
    maxIter = 1
    PORT = 10201
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('0.0.0.0', PORT))
    sock.listen(1)

    while True:
        c, a = sock.accept()
        cThread = threading.Thread(target=handler, args=(c,a,container,maxIter))
        cThread.daemon = True
        cThread.start()
        connections.append(c)
        print(connections)


if __name__ == "__main__":
    main()