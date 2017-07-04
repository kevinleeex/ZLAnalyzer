__author__ = 'Kevin T. Lee'
__time__ = '2017-07-01 10:03'

import os

import PIL.Image as Image
import jieba
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pymongo
from wordcloud import WordCloud, ImageColorGenerator

from config import *


class Analysis:
    def __init__(self, keyword, city=None):
        self.__keyword = keyword
        self.__df_city = None
        self.__city = city
        self.__df_city_main = self.__preference()

    def __preference(self):
        plt.style.use('ggplot')
        # to solve problem of displaying Chinese
        plt.rcParams['font.sans-serif'] = ['SimHei']  # default font
        plt.rcParams['axes.unicode_minus'] = False  # to solve the problem of displaying the box

        client = pymongo.MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        table = db[self.__keyword]

        columns = ['zwmc',  # 职位名称 Position
                   'gsmc',  # 公司名称 Name of Co.
                   'zwyx',  # 职位月薪 Monthly salary
                   'gbsj',  # 公布时间 Release date
                   'gzdd',  # 工作地点 Workplace
                   'fkl',  # 反馈率 Feedback
                   'brief',  # 简介 Brief brief
                   'zw_link',  # 网页链接 Website link
                   '_id',  # id
                   'date_saved']  # 保存日期 Date saved

        df = pd.DataFrame([records for records in table.find()], columns=columns)
        print('Total records：{}'.format(df.shape[0]))
        df.head(2)

        df['date_saved'] = pd.to_datetime(df['date_saved'])

        df_clean = df[['zwmc',
                       'gsmc',
                       'zwyx',
                       'gbsj',
                       'gzdd',
                       'fkl',
                       'brief',
                       'zw_link',
                       'date_saved']]

        # remove the records with unclear salaries.
        df_clean = df_clean[df_clean['zwyx'].str.contains('\d+-\d+', regex=True)]
        print('Total records after cleaning：{}'.format(df_clean.shape[0]))

        s_min, s_max = df_clean.loc[:, 'zwyx'].str.split('-', 1).str
        df_min = pd.DataFrame(s_min)
        df_min.columns = ['zwyx_min']
        df_max = pd.DataFrame(s_max)
        df_max.columns = ['zwyx_max']
        df_clean_concat = pd.concat([df_clean, df_min, df_max], axis=1)
        df_clean_concat['zwyx_min'] = pd.to_numeric(df_clean_concat['zwyx_min'])
        df_clean_concat['zwyx_max'] = pd.to_numeric(df_clean_concat['zwyx_max'])
        df_clean_concat.head(2)

        if self.__city is not None:
            df_city = df_clean_concat[df_clean_concat['gzdd'].str.contains(self.__city + '.*', regex=True)]
            print('There are ' + '{}'.format(df_city.shape[0]) + ' positions in ' + self.__city)
        else:
            df_city = df_clean_concat.copy()

        self.__df_city = df_city

        # Deal with the problem that workplaces with too much details.
        for city in ADDRESS:
            df_city['gzdd'] = df_city['gzdd'].replace([(city + '.*')], [city], regex=True)

        # Analysis of major cities in China
        df_city_main = df_city[df_city['gzdd'].isin(ADDRESS)]

        return df_city_main

    # To get top10 Cities in the position
    def top10City(self):
        try:
            if self.__city is not None:
                raise NameError('one city')
        except NameError:
            print('You are analysing only one city.')
            return

        df_city_main_count = self.__df_city_main.groupby('gzdd')['zwmc', 'gsmc'].count()

        df_city_main_count['gsmc'] = df_city_main_count['gsmc'] / (df_city_main_count['gsmc'].sum())

        df_city_main_count.columns = ['number', 'percentage']

        # sort by numbers of positions
        df_city_main_count.sort_values(by='number', ascending=False, inplace=True)

        # Add assistant columns to save label and percentage.
        df_city_main_count['label'] = df_city_main_count.index + ' ' + (
            (df_city_main_count['percentage'] * 100)).astype('int').astype('str') + '%'

        # Top10 list of positions number
        top10 = df_city_main_count.head(10)
        print(top10)
        with open(os.path.dirname(__file__)+'/../data/'+self.__keyword+'_top10_positions_nums.txt', 'w', encoding='utf-8') as f:
            f.write(top10.to_string())

        label = df_city_main_count['label']
        sizes = df_city_main_count['number']
        # Set the size of figure
        fig, axes = plt.subplots(figsize=(10, 6), ncols=2)
        ax1, ax2 = axes.ravel()
        # Too much cities labels and percentages will not be shown
        patches, texts = ax1.pie(sizes, shadow=False, startangle=0, colors=None)

        ax1.axis('equal')
        ax1.set_title(self.__keyword + ' 职位数量主要城市分布', loc='center')
        # ax2 only show the legend
        ax2.axis('off')
        ax2.legend(patches, label, loc='center left', fontsize=9)

        plt.savefig(os.path.dirname(__file__)+'/../images/' + self.__keyword + '_positions_distribution.png')
        # plt.show()

    # Nationwide salaries(Positions with excessive salaries have been removed)
    def salaryAnalysis(self):

        df_zwyx_adjust = self.__df_city[self.__df_city['zwyx_min'] <= 35000]
        if self.__city is not None:
            excel_filename = os.path.dirname(__file__)+'/../data/' + self.__keyword + '_zhilian_' + self.__city + '.xlsx'
        else:
            excel_filename = os.path.dirname(__file__)+'/../data/' + self.__keyword + '_zhilian_全国.xlsx'

        self.__df_city.to_excel(excel_filename)

        fig, ax2 = plt.subplots(figsize=(10, 8))
        y1 = df_zwyx_adjust['zwyx_min']
        bins = [3000, 6000, 9000, 12000, 15000, 18000, 21000, 32000]
        counts, bins, patches = ax2.hist(y1, bins, normed=1, histtype='bar', facecolor='#87CEFA', rwidth=0.8)
        if self.__city is None:
            ax2.set_title(self.__keyword+' 全国最低月薪直方图', size=14)
        else:
            ax2.set_title(self.__keyword + ' ' + self.__city + '最低月薪直方图', size=14)
        ax2.set_yticklabels('')
        ax2.set_xlabel('月薪（RMB）')

        ax2.set_xticks(bins)  # to set bins as xticks
        ax2.set_xticklabels(bins, rotation=-90)  # set the orientation of xticklabels

        # Label the raw counts and the percentages below the x-axis...
        bin_centers = 0.5 * np.diff(bins) + bins[:-1]

        for count, x in zip(counts, bin_centers):
            percent = '%0.0f%%' % (100 * float(count) / counts.sum())

            ax2.annotate(percent, xy=(x, 0), xycoords=('data', 'axes fraction'), xytext=(0, -40),
                         textcoords='offset points',
                         va='top', ha='center', rotation=-90, color='b', size=14)

        if self.__city is not None:
            fig_name = os.path.dirname(__file__)+'/../images/' + self.__keyword + '_salary_distribution_' + self.__city + '.png'
        else:
            fig_name = os.path.dirname(__file__)+'/../images/' + self.__keyword + '_salary_distribution_全国.png'
        fig.savefig(fig_name)

    # Save briefs of positions.
    def saveBrief(self):
        brief_list = list(self.__df_city['brief'])
        brief_str = ''.join(brief_list)
        if self.__city is None:
            filename = os.path.dirname(__file__)+'/../data/'+self.__keyword+'_brief_全国.txt'
        else:
            filename = os.path.dirname(__file__)+'/../data/'+self.__keyword+'_brief_' + self.__city + '.txt'

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(brief_str)

    # Generate words cloud figure
    def wordCloud(self):
        self.saveBrief()
        if self.__city is None:
            pfile = os.path.dirname(__file__)+'/../data/'+self.__keyword+'_brief_全国.txt'
        else:
            pfile = os.path.dirname(__file__)+'/../data/'+self.__keyword+'_brief_' + self.__city + '.txt'

        with open(pfile, 'rb') as f:  # 读取文件内容
            text = f.read()
            f.close()

        # Use jieba to cut Characters
        wordlist = jieba.cut(text, cut_all=False)
        # cut_all
        wordlist_space_split = ' '.join(wordlist)
        d = os.path.dirname(__file__)
        alice_coloring = np.array(Image.open(os.path.join(d, '../res/colors.jpg')))
        mask = np.array(Image.open(os.path.join(d, '../res/mask.png')))
        my_wordcloud = WordCloud(font_path=os.path.dirname(__file__)+'/../res/'+FONT, background_color='#F0F8FF', max_words=100, mask=mask,
                                 max_font_size=300, random_state=42).generate(wordlist_space_split)
        image_colors = ImageColorGenerator(alice_coloring)
        # plt.show(my_wordcloud.recolor(color_func=image_colors))
        plt.imshow(my_wordcloud)  # 以图片的形式显示词云
        plt.axis('off')  # 关闭坐标轴
        # plt.show()
        if self.__city is not None:
            cloud_filename = os.path.dirname(__file__)+'/../images/' + self.__keyword + '_words_cloud_' + self.__city + '.png'
        else:
            cloud_filename = os.path.dirname(__file__)+'/../images/' + self.__keyword + '_words_cloud_全国.png'
        my_wordcloud.to_file(os.path.join(d, cloud_filename))

    # All functions in one call
    def easyRun(self):
        self.top10City()
        self.salaryAnalysis()
        self.wordCloud()
