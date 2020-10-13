import scrapy
from urllib.parse import urlencode
import re
import json
import logging

home_garden_url = "https://www.amazon.com/s?i=garden&bbn=3295676011&&low-price=150&high-price="

class AmazonProductsWithTorSpider(scrapy.Spider):
    name = 'amazon_products_free_proxies'
    allowed_domains = ['amazon.com']

    def __init__(self):
        # define all of the xpaths here
        self.getAllProducts = '//*[@data-component-type="s-search-result"]'

    def start_requests(self):
        url = home_garden_url
        yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        products = response.xpath(self.getAllProducts)

        for product in products:
            asin = product.xpath('@data-asin').extract_first()
            product_url = f"https://www.amazon.com/dp/{asin}"
            yield scrapy.Request(url=product_url, callback=self.parse_product_details, meta={'asin': asin})

        # next_page = response.xpath('//li[@class="a-last"]/a/@href').extract_first()

        # if next_page:
        #     print(next_page)
        # if next_page:
        for i in range(1, 5):
            # url = response.urljoin(next_page)
            url = home_garden_url + f"page={i}"
            logging.info(url)
            yield scrapy.Request(url=get_url(url), callback=self.parse)

    def parse_product_details(self, response):
        asin = response.meta['asin']
        title = response.xpath('//*[@id="productTitle"]/text()').extract_first()
        image = re.search('"large":"(.*?)"', response.text).groups()[0]
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
        seller_rank = response.xpath(
            '//*[text()="Amazon Best Sellers Rank:"]/parent::*//text()[not(parent::style)]').extract()
        yield {'asin': asin, 'Title': title, 'MainImage': image, 'Rating': rating,
               'NumberOfReviews': number_of_reviews,
               'Price': price, 'AvailableSizes': sizes, 'AvailableColors': colors, 'BulletPoints': bullet_points,
               'SellerRank': seller_rank}
