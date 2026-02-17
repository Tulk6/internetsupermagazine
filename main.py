'''
Sources:
- ##youtube##
- ##rss##
- ##letterboxd##
- ##reddit##
- instagram
- bluesky
- twitter
- #tumblr#
- bandcamp
'''

#pyrinter

from datetime import datetime, timedelta, timezone
from PIL import Image, ImageChops, ImageStat
from io import BytesIO
import feedparser, pytumblr, requests, time, fpdf, random, pytube, moviepy, configparser
import md

#forget oauth - all should be possible outside of account
#dont wanna be using utube yk...


global_config = configparser.ConfigParser()
global_config.read('config.ini')


def get_image(url):
    return Image.open(BytesIO(requests.get(url).content))

class YoutubeVideo:
    def __init__(self, url):
        self.yt = pytube.YouTube(url)

        self.captions = self.yt.captions['en'].json_captions
        self.video = self.yt.streams.get_lowest_resolution()

    def compare_palettes(self, i1, i2):
        cols1 = i1.getcolors()
        cols2 = i2.getcolors()
        p1 = i1.getpalette()
        p2 = i2.getpalette()
        for col1 in p1:
            for col2 in p2:
                print(sum(col1-col2)/3)
        
    def video_comic(self):
        vid_path = self.video.download('./videos/')
        vid = moviepy.VideoFileClip(vid_path)

        frames = []
        frames.append(Image.fromarray(vid.get_frame(0)))
        frames[0].save(f'frames/0.jpg')
            
        for event in self.captions['events']:
            similar = False
            caption_time = event['tStartMs']//1000
            caption_text = event['segs'][0]['utf8'].replace('\n', '')
            #print(caption_text)
            frame = Image.fromarray(vid.get_frame(caption_time))

            #image luminosity difference
            for prev_frame in frames:
                dif_img = ImageChops.difference(frame, prev_frame).convert('L')
                dif_quant = ImageStat.Stat(dif_img).mean[0]

                #image palette difference
                #img_pal = frame.convert(mode='P', palette=Image.Palette.ADAPTIVE)
                #pre_pal = frames[-1].convert(mode='P', palette=Image.Palette.ADAPTIVE)
                #self.compare_palettes(img_pal, pre_pal)
                
                if dif_quant < 40:
                    similar = True
                    print('SIM!')
                    break

            if not similar:
                frames.append(frame)
                frame.save(f'frames/{caption_time}.jpg')
                print(caption_time)

                    
class Youtube:
    def __init__(self):
        pass

class Feed:
    def draw_page(self, date):
        pass

class RSS:
    def __init__(self, urls):
        self.urls = urls

    def published_after(self, published, since):
        date_published = datetime.fromtimestamp(time.mktime(published), tz=timezone.utc)#datetime.strptime(published, f'%a, %d %b %Y %H:%M:%S %z')
        if date_published > since:
            return date_published
        return False

    def get_feed_items(self, url):
        reader = feedparser.parse(url)
        return reader.entries

    def get_new_articles(self, since_datetime):
        new_articles = []
        for url in self.urls:
            for entry in self.get_feed_items(url):
                if date_published := self.published_after(entry.published_parsed, since_datetime):
                    if 'content' in entry: # if entry has 'content' then is an Atom feed and may have multiple contentes we need to rener
                        for content_item in entry.content:
                            if content_item.type == 'text/html': #if html, parse to md
                                document = md.convert(content_item.value)
                            else:
                                content_value = content_item.value
                            article = {'title': entry.title, 'author': entry.author, 'date published': date_published,
                               'document': document}
                            new_articles.append(article)
                    else:
                        # if no content in entry, then plain rss and use summary
                        content = entry.summary
                        content_type = entry.summary_detail.type
                        if content_type == 'text/html': #if html, parse to md
                            document = md.convert(content)
                        article = {'title': entry.title, 'author': entry.author, 'date published': date_published,
                                   'document': document}
                        new_articles.append(article)

        return new_articles

    def draw_page(self, pdf, since_datetime):
        articles = self.get_new_articles(since_datetime)
        random.shuffle(articles)

        pdf.set_font('Heading Serif', '', 8)
        pdf.cell(0, None, 'RSS', new_x="LMARGIN", new_y='NEXT', align='C')
        pdf.ln(None)

        for article in articles:
            pdf.cell(0, None, article['title'], new_x='LEFT', new_y='NEXT', markdown=True)
            pdf.multi_cell(0, None, article['content'], new_x='LEFT', new_y='NEXT', markdown=True)


class WikipediaFeatured(RSS):
    def __init__(self):
        super().__init__(['https://en.wikipedia.org/w/api.php?action=featuredfeed&feed=featured'])

    def draw_article(self, pdf, article):
        content = article['document'].text[0].split('__(Full article...)__')[0]
        title = article['title'][:-27] #getting rid of wikipedia featured article....
        pdf.set_font('Heading Serif', 'b', 8)
        pdf.cell(0, None, title, new_x='LEFT', new_y='NEXT', markdown=True)
        #if len(article['document'].images) != 0:
            #print(article['document'].images)
            #pdf.image(article['document'].images[0])
        pdf.set_font('Body Serif', '', 8)
        pdf.multi_cell(0, None, content, new_x='LEFT', new_y='NEXT', markdown=True)
    
    def draw_page(self, pdf, since_datetime):
        articles = self.get_new_articles(since_datetime)
        articles.sort(key=lambda x: len(x['document'].text[0]), reverse=True)

        pdf.set_font('Heading Serif', '', 8)
        pdf.cell(0, None, 'RSS', new_x="LMARGIN", new_y='NEXT', align='C')
        pdf.ln(None)

        for article in articles:
            with pdf.offset_rendering() as dummy:
                self.draw_article(pdf, article)
            if dummy.page_break_triggered:
                continue
            else:
                self.draw_article(pdf, article)

class Letterboxd(RSS):
    def __init__(self, users):
        self.omdb_key = global_config['Letterboxd']['omdb_key']
        self.users = users

    def get_movie_details(self, title, year):
        data = {'Plot': '', 'Director': '', 'Actors': ''}
        data.update(requests.get(f'http://www.omdbapi.com/?t={title}&y={year}&apikey={self.omdb_key}').json())
        return data

    def get_user_activity(self, username):
        return self.get_feed_items(f'https://letterboxd.com/{username}/rss/')

    def get_new_articles(self, since_datetime):
        new_articles = []
        for user in self.users:
            for entry in self.get_user_activity(user):
                if date_published := self.published_after(entry.published_parsed, since_datetime):
                    movie_details = self.get_movie_details(entry.letterboxd_filmtitle, entry.letterboxd_filmyear)
                    review_doc = md.convert(entry.summary)
                    if review_doc.text[0][:10] == 'Watched on':
                        #no actual review, just auto generated part
                        continue
                    title = entry.title
                    if entry.letterboxd_memberlike == 'Yes':
                        title += ' ♥'
                    image = get_image(review_doc.images[0])
                    article = {'title': title, 'author': entry.author, 'date published': date_published,
                               'summary': movie_details['Plot'], 'director': movie_details['Director'],
                               'actors': movie_details['Actors'], 'review': review_doc.full_text, 'image': image}
                    new_articles.append(article)

        return new_articles

    def draw_page(self, pdf, since_datetime):
        articles = self.get_new_articles(since_datetime)
        random.shuffle(articles)

        
        pdf.set_font('Heading Serif', '', 8)
        pdf.cell(0, None, 'LETTERBOXD REVIEWS', new_x="LMARGIN", new_y='NEXT', align='C')
        pdf.ln(None)

        for article in articles:
            start_y = pdf.y
            img_result = pdf.image(article['image'], w=pdf.epw/6)
            pdf.x += img_result.rendered_width+1
            pdf.y -= img_result.rendered_height
            pdf.set_font('Heading Serif', '', 12)
            pdf.cell(0, None, article['title'], new_x='LEFT', new_y='NEXT')
            pdf.cell(pdf.epw/2-5, None, f'__{article["director"]}, staring {article["actors"]}__', new_x='LEFT', new_y='NEXT', markdown=True)
            pdf.set_font('Body Serif', 'i', 8)
            pdf.multi_cell(0, None, article['summary'], new_x='LEFT', markdown=True)
            pdf.set_font('Body Serif', '', 8)
            pdf.multi_cell(0, None, article['review']+'\nby '+article['author'], new_x='LEFT', markdown=True)
            pdf.cell(0, None, new_x='LMARGIN', new_y='NEXT')
            if pdf.y > start_y:
                pdf.y = max(pdf.y, start_y+img_result.rendered_height+1)
            


class Magazine:
    def __init__(self, feeds):
        self.feeds = feeds

    def draw_title(self, pdf):
        pass

    def generate_magazine(self):
        pdf = PDF(format='a5')

        pdf.add_page()
        self.draw_title(pdf)
        
        for feed in self.feeds:
            pdf.add_page()
            feed.draw_page(pdf, (datetime.now(timezone.utc)-timedelta(weeks=1)))

        pdf.output('test.pdf')


class PDF(fpdf.FPDF):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add_font("Body Serif", fname='fonts/times.ttf')
        self.add_font("Body Serif", style='i', fname='fonts/timesi.ttf')

        self.add_font("Heading Serif", fname='fonts/Junicode-Cond.otf')
        self.add_font("Heading Serif", style='i', fname='fonts/Junicode-CondItalic.otf')
        self.add_font("Heading Serif", style='b', fname='fonts/HiroshigeStd-Bold.ttf')
        self.add_font("Heading Serif", style='ib', fname='fonts/HiroshigeStd-BoldItalic.ttf')
        
        self.add_font("Segoe Symbol", fname='fonts/seguisym.ttf')
        self.add_font("Segoe Emoji", fname='fonts/seguiemj.ttf')
        self.set_fallback_fonts(['Segoe Symbol', 'Segoe Emoji'])

        self.set_text_shaping(True)
        
    def print_article(self, article):
        self.add_page()
        self.set_font('Junicode', '', 12)
        self.cell(0, None, article.title, new_x=fpdf.XPos.LMARGIN, new_y=fpdf.YPos.NEXT)
        self.multi_cell(0, None, article.content, new_x=fpdf.XPos.LMARGIN)

#vid = YoutubeVideo('https://www.youtube.com/watch?v=a9uDlsS5ASk')

#vid.video_comic()

mag = Magazine([Letterboxd(['embassyrow', 'iiingriddd', 'dav1dthedancer', 'jammesros', '_scarl3tt', 'gracepedatrican', 'lucythatone', 'notgoodatchess'])])
                #WikipediaFeatured()]) 
mag.generate_magazine()

#rss = Reddit()
#rss.subreddits = ['twosentencehorror']
#print(rss.get_new_articles(datetime.now(timezone.utc)-timedelta(hours=48)))





