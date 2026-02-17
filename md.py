from html.parser import HTMLParser

class Image:
    def __init__(self, url):
        self.url = url

class Text:
    def __init__(self, md):
        self.md = md

class Document:
    def __init__(self):
        self.content = []

    def add_image(self, url):
        self.content.append(Image(url))

    def add_text(self, md):
        self.content.append(Text(md))

    @property
    def full_text(self):
        return '\n'.join(self.text)

    @property
    def images(self):
        return [item.url for item in self.content if type(item) is Image]

    @property
    def text(self):
        return [item.md for item in self.content if type(item) is Text]
        

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.document = Document()

        self.current_text = ''

    def get_attr_value(self, name, attrs):
        for attr_name, value in attrs:
            if attr_name == name:
                return value

    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            self.current_text = ''
        elif tag == 'img':
            self.document.add_image(self.get_attr_value('src', attrs))
        elif tag == 'i':
            self.current_text += '__'
        else:
            pass
            #print(tag, attrs)

    def handle_endtag(self, tag):
        if tag == 'p':
            if self.current_text != '':
                self.document.add_text(self.current_text)
                self.current_text = ''
        elif tag == 'i':
            while self.current_text[-1] == ' ':
                self.current_text = self.current_text[:-1]
            self.current_text += '__ '
        else:
            pass
            #print('end', tag)

    def handle_data(self, data):
        if not data.isspace():
            self.current_text += data

    def refresh(self):
        self.close()
        self.reset()
        
        self.document = Document()
        self.current_text = ''


def convert(html):
    parser = Parser()
    parser.feed(html)
    return parser.document
