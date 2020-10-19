import scrapy
from urllib.parse import urlencode
import re
import json
from ..items import Product
import logging
API = '0dabb38ed3e0603f8b4f1a354a443476'


def paginate_url(page):
    home_garden_url = f"https://www.amazon.com/s?i=garden&bbn=3295676011&rh=p_36%3A15000-&qid=1602614531&ref=sr_pg_{str(page)}&page={str(page)}"
    return home_garden_url


def get_url(url):
    # payload = {'api_key': API, 'url': url, 'country_code': 'us'}
    # proxy_url = 'http://api.scraperapi.com/?' + urlencode(payload)
    # return proxy_url
    return url


def clean_text(text):
    new_text = " ".join(text.split()).strip()
    if "\\" in new_text:
        remove_escaped_chars = new_text.replace('\\', '')
        return remove_escaped_chars
    else:
        return new_text


class AmazonSpider(scrapy.Spider):
    name = 'amazon_products_with_proxy'
    allowed_domains = ['amazon.com', 'api.scraperapi.com']
    page = 1
    product = Product()

    # def start_requests(self):
    #     url = get_url(home_garden_url)
    #     yield scrapy.Request(url=url, callback=self.parse)

    # Debugging: Product Details Page
    def start_requests(self):
        # sold by amazon = True
        # url = 'https://www.amazon.com/dp/B08J5Y89C7?ref=ods_ucc_kindle_B08J5Y89C7_rc_nd_ucc'
        # sold by amazon = False
        url = 'https://www.amazon.com/Linon-PG139WHT01U-Desk-White/dp/B07FDHMDD3/ref=sr_1_2415?dchild=1&qid=1602868163&refinements=p_36%3A15000-&s=home-garden&sr=1-2415'
        yield scrapy.Request(url=get_url(url), callback=self.parse_product_details)

    def parse(self, response):

        products = response.xpath('//*[@data-component-type="s-search-result"]')

        for product in products:

            is_prime = product.xpath('.//*[@aria-label="Amazon Prime"]')
            logging.info(is_prime)

            if not is_prime:
                asin = product.xpath('@data-asin').extract_first()

                product_url = f"https://www.amazon.com/dp/{asin}"

                price = None
                title = None

                meta = {
                    "isPrime": is_prime,
                    "asin": asin,
                    "url": product_url,
                    "title": title,
                    "price": price
                }

                yield scrapy.Request(url=get_url(product_url), callback=self.parse_product_details, meta=meta)

        # TODO: enable for production
        # next_page = response.xpath('//li[@class="a-last"]/a/@href').extract_first()
        #
        # if next_page:
        #     logging.info(next_page)
        #     url = f"https://www.amazon.com{next_page}"
        #     logging.info(url)
        #     yield scrapy.Request(url=get_url(url), callback=self.parse)

        # TODO: Disable for production

        if self.page < 4:
            self.page += 1
            url = paginate_url(self.page)
            logging.info(url)
            yield scrapy.Request(url=get_url(url), callback=self.parse)

    def parse_buying_options(self, response):
        # only run if prop is not already assigned
        # get main sellers name
        # TODO: redo
        def get_sold_by():
            has_see_more_link = response.css("#aod-pinned-offer-show-less-link")
            has_pinned_offer = response.css("#aod-pinned-offer")
            if has_see_more_link or has_pinned_offer:
                return clean_text(response.css(
                    "#aod-pinned-offer-additional-content #aod-offer-soldBy span.a-size-small.a-color-base::text").get())
            else:
                return clean_text(response.css('#aod-offer-soldBy [role="link"]::text').get())
            pass

        # get sold by
        if 'soldBy' not in self.product:
            self.product['soldBy'] = get_sold_by()
        # get third party seller price
        if 'price' not in self.product:
            # TODO: convert to a functions
            # self.product['price'] = get_price()
            self.product['price'] = response.css(".a-price-whole::text").get()
        # Number of sellers on the listing
        if 'sellers' not in self.product:
            # TODO: convert to a functions
            # self.product['sellers'] = get_sellers()
            self.product['sellers'] = response.css("#aod-total-offer-count::attr(value)").get()

        yield self.product

    def parse_product_details(self, response):

        more_options_url = response.css("#olp-upd-new-used a::attr(href)").get()

        if response.meta:
            # set props to meta values if available
            # set price
            # set asin
            # set isPrime
            # set title
            # set url
            pass

        def get_asin():

            asin_string = response.css("link[rel='canonical']::attr(href)").get()
            if asin_string:
                asin_pattern = re.compile(r"dp/([A-Z0-9]{10})")
                asin = asin_pattern.search(asin_string)[1]

                return asin
            else:
                return None

        def get_sold_by_amazon():

            # get the node
            node = response.css("td .a-truncate.buybox-tabular-content.a-size-small").get()
            # if node
            # remove any extra white space
            if node:
                # check to see if text inside node includes "sold by Amazon.com"
                has_text = "Amazon.com" in node
                # if True set to "true" if False set to "false"
                if has_text:
                    return "true"
                else:
                    return "false"
            else:
                return "false"

        def get_bsr():

            bsr_selectors = [
                '#productDetails_detailBullets_sections1',
                '#productDetails_db_sections',
                '#detailBulletsWrapper_feature_div'
            ]

            for selector in bsr_selectors:
                # loop through all of the selector to see which one is true
                product_info_node = response.css(selector).get()

                if product_info_node:
                    bsr_pattern = re.compile("<span>#(\d*,?\d*,?\d*)")
                    matches = bsr_pattern.findall(product_info_node)
                    bsr_text = matches[0].replace(",", '')
                    bsr = int(bsr_text)
                    return bsr
                else:
                    return None

        def get_fba():

            fba_node = response.css("#buybox::text").get()

            if fba_node:
                has_fba = "Fulfilled" in fba_node

                if has_fba:
                    return "true"
                else:
                    return "false"
            else:
                return "false"

        def get_about_bullets():

            about_bullets = response.xpath("//*[@id='feature-bullets']/ul/li")

            if about_bullets:

                all_about_bullets = []

                for bullet in about_bullets:
                    bullet_text = bullet.xpath('.//span/text()').get()
                    single_bullet = clean_text(bullet_text)
                    all_about_bullets.append(single_bullet)

                return all_about_bullets
            else:
                return None

        def get_description():

            description_node = response.css("#productDescription > p span::text").get()

            if description_node:
                return clean_text(description_node)
            else:
                return None

        def get_title():
            title_text = response.css("#productTitle::text").get()
            title = clean_text(title_text)
            return title

        def get_image_urls():
            return None

        def get_in_stock():
            in_stock_node = response.css("#availabilityInsideBuyBox_feature_div #availability span::text").get()

            if in_stock_node:
                in_stock_text = clean_text(in_stock_node)
                if "In Stock" in in_stock_text:
                    return "true"
                else:
                    return "false"

        def get_buy_box():
            buy_box_node = response.css("#add-to-cart-button").get()
            if buy_box_node:
                return 'true'
            else:
                return 'false'

        def get_rating():
            rating_node = response.css("#acrPopover").get()
            if rating_node:
                rating_pattern = re.compile(r'(\d+\.\d+|\d+)')
                rating_text = rating_pattern.search(rating_node)
                rating = float(rating_text[0])
                return rating
            else:
                return None

        def get_total_reviews():
            return None
            pass

        def get_sold_by():
            sold_by_node = response.css("#buyboxTabularTruncate-1 span::text").get()
            if sold_by_node:
                sold_by = clean_text(sold_by_node)
                return sold_by
            else:
                return None

        def get_sellers():
            sellers_node = response.css("#olp-upd-new-used a span:nth-child(1)::text").get()
            if sellers_node:
                sellers_text = clean_text(sellers_node)
                sellers_pattern = re.compile(r"\((\d+)\)")
                sellers_match = sellers_pattern.search(sellers_text)[1]
                sellers = int(sellers_match)
                return sellers
            else:
                return None

        def get_price():
            price_node = response.css("#priceblock_ourprice::text").get()
            if price_node:
                price_pattern = re.compile(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})")
                price_text = clean_text(price_node)
                price_match = price_pattern.search(price_text)[0]
                price = float(price_match)
                return price
            else:
                return None

        if 'asin' not in self.product:
            self.product['asin'] = get_asin()

        if 'title' not in self.product:
            self.product['title'] = get_title()

        if 'price' not in self.product:
            self.product['price'] = get_price()

        self.product['category'] = "Home & Kitchen"
        self.product['bsr'] = get_bsr()
        self.product['soldByAmazon'] = get_sold_by_amazon()
        self.product['rating'] = get_rating()
        self.product['isFba'] = get_fba()
        self.product['aboutBullets'] = get_about_bullets()
        self.product['description'] = get_description()
        self.product['hasBuyBox'] = get_buy_box()
        self.product['inStock'] = get_in_stock()
        self.product['soldBy'] = get_sold_by()
        self.product['sellers'] = get_sellers()

        # self.product['imageUrls'] = get_image_urls()
        # self.product['totalReviews'] = get_total_reviews()

        # after harvesting all of the product details make second request for the rest of the data
        # only execute 2nd call if the extra categories are missing

        # TODO: convert this to a function
        if 'asin' in self.product and more_options_url:

            buying_options_btn = response.css("#buybox-see-all-buying-choices-announce").get()
            more_sellers_link = response.css("#olp-upd-new").get()
            availability = response.css("#availability").get()
            asin = self.product['asin']

            if buying_options_btn or more_sellers_link or availability:
                url = f"https://www.amazon.com/gp/aod/ajax/ref=dp_olp_ALL_mbc?asin={asin}"
                buying_options_url = get_url(url)
                yield scrapy.Request(url=buying_options_url, callback=self.parse_buying_options)
            else:
                yield self.product
