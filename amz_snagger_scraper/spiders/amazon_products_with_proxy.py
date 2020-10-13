import scrapy
from urllib.parse import urlencode
import re
import json
import logging
API = '0dabb38ed3e0603f8b4f1a354a443476'

def paginate_url(page):
    home_garden_url = f"https://www.amazon.com/s?i=garden&bbn=3295676011&rh=p_36%3A15000-&qid=1602614531&ref=sr_pg_{str(page)}&page={str(page)}"
    return home_garden_url

def get_url(url):
    payload = {'api_key': API, 'url': url, 'country_code': 'us'}
    proxy_url = 'http://api.scraperapi.com/?' + urlencode(payload)
    return proxy_url

class AmazonSpider(scrapy.Spider):
    name = 'amazon_products_with_proxy'
    allowed_domains = ['amazon.com', 'api.scraperapi.com']
    page = 1

    def __init__(self):
        # define all of the xpaths here
        self.getAllProducts = '//*[@data-component-type="s-search-result"]'

    def start_requests(self):
        url = get_url(home_garden_url)
        yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        products = response.xpath(self.getAllProducts)
        for product in products:

            has_prime = product.xpath('.//*[@aria-label="Amazon Prime"]')
            logging.info(has_prime)

            if not has_prime:
                asin = product.xpath('@data-asin').extract_first()
                product_url = f"https://www.amazon.com/dp/{asin}"
                yield scrapy.Request(url=get_url(product_url), callback=self.parse_product_details, meta={'asin': asin})

        # next_page = response.xpath('//li[@class="a-last"]/a/@href').extract_first()
        #
        # if next_page:
        #     logging.info(next_page)
        #     url = f"https://www.amazon.com{next_page}"
        #     logging.info(url)
        #     yield scrapy.Request(url=get_url(url), callback=self.parse)

        if self.page < 4:
            self.page += 1
            url = paginate_url(self.page)
            logging.info(url)
            yield scrapy.Request(url=get_url(url), callback=self.parse)

    def parse_product_details(self, response):
        asin = response.meta['asin']
        title = response.xpath('//*[@id="productTitle"]/text()').extract_first()
        image = re.search('"large":"(.*?)"',response.text).groups()[0]
        rating = response.xpath('//*[@id="acrPopover"]/@title').extract_first()
        number_of_reviews = response.xpath('//*[@id="acrCustomerReviewText"]/text()').extract_first()
        price = response.xpath('//*[@id="priceblock_ourprice"]/text()').extract_first()

        if not price:
            price = response.xpath('//*[@data-asin-price]/@data-asin-price').extract_first() or \
                    response.xpath('//*[@id="price_inside_buybox"]/text()').extract_first()

        temp = response.xpath('//*[@id="twister"]')
        sizes = []
        colors = []
        if temp:
            s = re.search('"variationValues" : ({.*})', response.text).groups()[0]
            json_acceptable = s.replace("'", "\"")
            di = json.loads(json_acceptable)
            sizes = di.get('size_name', [])
            colors = di.get('color_name', [])

        bullet_points = response.xpath('//*[@id="feature-bullets"]//li/span/text()').extract()
        seller_rank = response.xpath('//*[text()="Amazon Best Sellers Rank:"]/parent::*//text()[not(parent::style)]').extract()
        yield {'asin': asin, 'Title': title, 'MainImage': image, 'Rating': rating, 'NumberOfReviews': number_of_reviews,
               'Price': price, 'AvailableSizes': sizes, 'AvailableColors': colors, 'BulletPoints': bullet_points,
               'SellerRank': seller_rank}