import calendar
# import seaborn as sns
import datetime

import pandas as pd
import streamlit as st


def get_file_name(file):
    # ファイル名から年月文字列を取得
    file_name = file.name.split('.')[0].split('_')[-1]
    return file_name


def get_eom(str_date):
    # ファイル名から月末日付を取得

    year = int(str_date[:4])
    month = int(str_date[-2:])
    last_day = calendar.monthrange(year, month)[1]

    eom = datetime.date(year, month, last_day).strftime('%Y/%m/%d')
    return eom


@st.cache
def load_file(file):
    df = pd.read_csv(file, encoding='cp932')
    return df


# --- 仕訳データの変換処理 ----
def filtered_df(df):
    # 並び替えとカラムの整理、リネーム
    df = df.filter(
        ['借方科目コード', '借方科目名称', '借方科目別補助コード', '借方科目別補助名称', '借方部門コード', '借方部門名称',
         '借方セグメント2', '借方セグメント２名称', '貸方科目コード', '貸方科目名称', '貸方科目別補助コード', '貸方科目別補助名称',
         '貸方部門コード', '貸方部門名称', '貸プセグメント2コード', '貸方セグメント２名称', '金額', '消費税', '摘要']) \
        .set_axis(['dr_cd', 'dr_name', 'dr_sub_cd', 'dr_sub_name', 'dr_section_cd', 'dr_section_name', 'dr_segment_cd',
                   'dr_segment_name',
                   'cr_cd', 'cr_name', 'cr_sub_cd', 'cr_sub_name', 'cr_section_cd', 'cr_section_name', 'cr_segment_cd',
                   'cr_segment_name',
                   'price', 'tax', 'outline'], axis=1
                  )
    return df


def convert_df(file):
    # 元ファイルの読み込み
    df = load_file(file)
    # コードの変換とフィルター
    filtered = filtered_df(df)
    return filtered


def copy_dataframe(df):
    _df = df.copy().assign(price=lambda x: df['price'] - df['tax']).drop('tax', axis=1)
    return _df


# -- 借方データ --
def convert_dr(df):
    df = copy_dataframe(df)

    # 貸方項目を削除
    _df = df.drop(
        ['cr_cd', 'cr_name', 'cr_sub_cd', 'cr_sub_name', 'cr_section_cd',
         'cr_section_name', 'cr_segment_cd', 'cr_segment_name'], axis=1
    ).dropna(subset='dr_cd').fillna(0)

    # カラムをリネーム
    _df.columns = ['ac_cd', 'ac_name', 'sub_cd', 'sub_name', 'section_cd', 'section_name', 'segment_cd',
                   'segment_name', 'price', 'outline']

    return _df


def calc_dr(df):
    df = convert_dr(df)

    df_sales = df.query('5000 <= ac_cd < 6000').assign(price=df['price'] * -1)
    df_cost = df.query('6000 <= ac_cd <= 7999')
    df_extra_income = df.query('8000 <= ac_cd < 8200').assign(price=df['price'] * -1)
    df_extra_outcome = df.query('8200 <= ac_cd < 8300')
    df_dr = pd.concat([df_sales, df_cost, df_extra_income, df_extra_outcome]).query('price != 0')

    return df_dr


# -- 貸方データ --
def convert_cr(df):
    df = copy_dataframe(df)

    # 貸方項目を削除
    _df = df.drop(
        ['dr_cd', 'dr_name', 'dr_sub_cd', 'dr_sub_name', 'dr_section_cd',
         'dr_section_name', 'dr_segment_cd', 'dr_segment_name'], axis=1
    ).dropna(subset='cr_cd').fillna(0)

    # カラムをリネーム
    _df.columns = ['ac_cd', 'ac_name', 'sub_cd', 'sub_name', 'section_cd', 'section_name', 'segment_cd',
                   'segment_name', 'price', 'outline']

    return _df


def calc_cr(df):
    df = convert_cr(df)

    df_sales = df.query('5000 <= ac_cd < 6000')
    df_cost = df.query('6000 <= ac_cd <= 7999').assign(price=df['price'] * -1)
    df_extra_income = df.query('8000 <= ac_cd < 8200')
    df_extra_outcome = df.query('8200 <= ac_cd < 8300').assign(price=df['price'] * -1)
    df_cr = pd.concat([df_sales, df_cost, df_extra_income, df_extra_outcome]).query('price != 0')

    return df_cr


# -- データ統合 --
def concat_drcr(dr, cr):
    df = pd.concat([dr, cr]).reset_index(drop=True)
    df.dropna(subset='ac_cd', inplace=True)
    # 型変換
    df['ac_cd'] = df['ac_cd'].apply(lambda x: str(int(x)))
    df['sub_cd'] = df['sub_cd'].apply(lambda x: str(int(x)))
    df['section_cd'] = df['section_cd'].apply(lambda x: str(int(x)))
    df['segment_cd'] = df['segment_cd'].apply(lambda x: str(int(x)))
    df['price'] = df['price'].apply(lambda x: int(x))

    return df


# --  Wide to Long 変換 --
# 集計用区分の辞書定義
large_class = {'CATV': 'コンシューマ事業',
               'ｺﾐｭﾆﾃｨﾁｬﾝﾈﾙ': 'コンシューマ事業',
               'NET': 'コンシューマ事業',
               'TEL': 'コンシューマ事業',
               'ｺﾐｭﾆﾃｨFM': 'まちづくり事業',
               'ｱﾌﾟﾘ(外販)': 'コンシューマ事業',
               'ｲﾍﾞﾝﾄ': 'まちづくり事業',
               '音響・照明': 'まちづくり事業',
               'ｿﾘｭｰｼｮﾝ': 'まちづくり事業',
               'ｽﾀｲﾙ': 'まちづくり事業',
               'ｼｮｯﾋﾟﾝｸﾞ': 'まちづくり事業',
               'ﾅﾋﾞ': 'まちづくり事業',
               'KURUTOｶﾌｪ': 'まちづくり事業',
               '指定管理': 'まちづくり事業',
               '子会社取引': 'グループ管理'}

mid_class = {'CATV': '放送',
             'ｺﾐｭﾆﾃｨﾁｬﾝﾈﾙ': '放送',
             'NET': '通信',
             'TEL': '通信',
             'ｺﾐｭﾆﾃｨFM': 'コミュニティFM',
             'ｱﾌﾟﾘ(外販)': 'アプリ',
             'ｲﾍﾞﾝﾄ': 'イベント',
             '音響・照明': 'イベント',
             'ｿﾘｭｰｼｮﾝ': 'ソリューション',
             'ｽﾀｲﾙ': 'ちたまる',
             'ｼｮｯﾋﾟﾝｸﾞ': 'ちたまる',
             'ﾅﾋﾞ': 'ちたまる',
             'KURUTOｶﾌｪ': 'KURUTO',
             '指定管理': 'KURUTO',
             '子会社取引': 'グループ取引'}


# 縦変換
def melt_df(df):
    df = df.filter(['科目CD', '科目名', '補助科目CD', '補助科目名', '部門CD', '部門名', '集計区分', 'CATV', 'ｺﾐｭﾆﾃｨﾁｬﾝﾈﾙ', 'NET', 'TEL',
                    'ｺﾐｭﾆﾃｨFM', 'ｱﾌﾟﾘ(外販)', 'ｲﾍﾞﾝﾄ', '音響・照明', 'ｿﾘｭｰｼｮﾝ', 'ｽﾀｲﾙ', 'ｼｮｯﾋﾟﾝｸﾞ', 'ﾅﾋﾞ', 'KURUTOｶﾌｪ', '指定管理',
                    '子会社取引']) \
        .melt(id_vars=['科目CD', '科目名', '補助科目CD', '補助科目名', '部門CD', '部門名', '集計区分'],
              var_name='s_class',
              value_vars=['CATV', 'ｺﾐｭﾆﾃｨﾁｬﾝﾈﾙ', 'NET', 'TEL',
                          'ｺﾐｭﾆﾃｨFM', 'ｱﾌﾟﾘ(外販)', 'ｲﾍﾞﾝﾄ', '音響・照明', 'ｿﾘｭｰｼｮﾝ', 'ｽﾀｲﾙ', 'ｼｮｯﾋﾟﾝｸﾞ', 'ﾅﾋﾞ', 'KURUTOｶﾌｪ',
                          '指定管理', '子会社取引'],
              value_name='金額')
    return df


# 区分追加
def add_mapping(df):
    df = df \
        .assign(large_class=df['s_class'].map(large_class)) \
        .assign(mid_class=df['s_class'].map(mid_class))
    return df


# 一連の変換処理
def load_long_data(df):
    df = load_file(df)
    df = melt_df(df)
    df = add_mapping(df)
    df= df.fillna(0)
    df.dropna(subset='金額', inplace=True)
    df['科目CD'] = df['科目CD'].apply(lambda x: str(int(x)))
    df['補助科目CD'] = df['補助科目CD'].apply(lambda x: str(int(x)))
    df['部門CD'] = df['部門CD'].apply(lambda x: str(int(x)))
    # df['金額'] = df['金額'].apply(lambda x: float(x))
    return df

@st.cache
def convert_to_csv(df, index=False):
    return df.to_csv().encode('cp932')


def main():
    """
    Streamlit Application
    :return:
    """

    # ヘッダーセクション
    st.title('仕訳データの分析用変換ツール')
    st.caption('振替伝票仕訳データを使った、データ分析用コード変換処理')

    # サイドバーセクション
    side_header = st.sidebar.container()
    side_header.write('--FILE UPLOADER--')
    side_header.write('#### 1.振替伝票 → 単票形式')

    uploaded_file = side_header.file_uploader('ファイル名：◯◯◯◯_YYYYMM', type='csv')

    side_header.write('---')

    side_header.write('#### 2.配賦データ → 縦変換')

    flg_box = side_header.radio('予算/実績の区分を選択', ('実績', '予算'))
    uploaded_wide_file = side_header.file_uploader('ファイル名: ◯◯◯◯_YYYYMM', type='csv')

    # メインセクション
    container_main = st.container()
    container_main.write('---')

    # １次処理用
    if uploaded_file is not None:
        # get_ym = get_file_name(uploaded_file)

        # ファイルの読み込み
        df = convert_df(uploaded_file)

        # 借方データの変換
        df_dr = calc_dr(df)

        # 貸方データの変換
        df_cr = calc_cr(df)

        # 短表データの連結
        df_concat = concat_drcr(df_dr, df_cr)

        container_main.subheader('1-1. Result - Details')
        data_size = df_concat.memory_usage().sum()

        show_detail = container_main.checkbox('Check & Preview - Details!')

        if show_detail:
            container_main.dataframe(df_concat, use_container_width=True)

        output_result_detail = convert_to_csv(df_concat)

        container_main.download_button(
            label='DL: 詳細データ',
            data=output_result_detail,
            file_name=f'result_detail_{get_file_name(uploaded_file)}.csv',
            mime='text/csv'
        )
        container_main.caption(
            f'参考）サイズ: {df_concat.shape},　容量: {data_size / 1024:.1f} MB, データ欠損値: {df_concat.isnull().any().sum()}')

        container_main.write('---')
        container_main.subheader('1-2. Result - Grouped')

        show_grouped = container_main.checkbox('Check & Preview - Grouped!')

        pivot_data = pd.pivot_table(df_concat,
                                    index=['ac_cd', 'ac_name', 'sub_cd', 'sub_name', 'section_cd',
                                           'section_name', 'segment_cd', 'segment_name'], values='price',
                                    aggfunc=sum).reset_index()

        data_size = pivot_data.memory_usage().sum()

        output_result_grouped = convert_to_csv(pivot_data)

        if show_grouped:
            container_main.dataframe(pivot_data, use_container_width=True)

        container_main.download_button(
            label='DL: 集計データ',
            data=output_result_grouped,
            file_name=f'result_{get_file_name(uploaded_file)}.csv',
            mime='text/csv'
        )

        container_main.caption(
            f'データサイズ: {pivot_data.shape},　容量: {data_size / 1024:.1f} MB, データ欠損値: {pivot_data.isnull().any().sum()}')
        container_main.write('---')

        container_main.write('NEXT ... 【集計データをダウンロードして、配賦結果を作成】')

    else:
        container_main.write('左側のメニューからファイルをアップロードしてください。')

    # 縦変換用処理
    if uploaded_wide_file is not None:

        df = load_long_data(uploaded_wide_file)

        if flg_box == '実績':
            df['予算/実績'] = '実績'
            df['期間'] = get_eom(get_file_name(uploaded_wide_file))

        elif flg_box == '予算':
            df['予算/実績'] = '予算'
            df['期間'] = get_eom(get_file_name(uploaded_wide_file))

        else:
            df['予算/実績'] = ''
            df['期間'] = get_eom(get_file_name(uploaded_wide_file))

        df_result_long = df.filter(
            ['予算/実績', '期間', '科目CD', '科目名', '補助科目CD', '補助科目名', '部門CD', '部門名', '集計区分', 's_class', 'mid_class',
             'large_class', '金額'])

        df_sales_long = \
            df_result_long \
                .query('集計区分 in ["利用料収入", "その他収入"]')

        df_cost_long = \
            df_result_long \
                .query('集計区分 not in ["利用料収入", "その他収入"]')

        container_main.subheader('2-1. Result - Sales_long')
        data_size = df_sales_long.memory_usage().sum()

        show_sales_long = container_main.checkbox('Check & Preview - sales_long')

        if show_sales_long:
            container_main.dataframe(df_sales_long, use_container_width=True)

        output_result_sales_long = convert_to_csv(df_sales_long)

        container_main.download_button(
            label='DL: 売上データ（long型）',
            data=output_result_sales_long,
            file_name=f'result_sales_long_{get_file_name(uploaded_wide_file)}.csv',
            mime='text/csv'
        )
        container_main.caption(
            f'参考）サイズ: {df_sales_long.shape},　容量: {data_size / 1024:.1f} MB, データ欠損値: {df_sales_long.isnull().any().sum()}')

        container_main.write('---')

        container_main.subheader('2-2. Result - Cost_long')
        data_size = df_cost_long.memory_usage().sum()

        show_cost_long = container_main.checkbox('Check & Preview - Cost_long')

        if show_cost_long:
            container_main.dataframe(df_cost_long, use_container_width=True)

        output_result_cost_long = convert_to_csv(df_cost_long)

        container_main.download_button(
            label='DL: 経費データ（long型）',
            data=output_result_cost_long,
            file_name=f'result_cost_long_{get_file_name(uploaded_wide_file)}.csv',
            mime='text/csv'
        )
        container_main.caption(
            f'参考）サイズ: {df_cost_long.shape},　容量: {data_size / 1024:.1f} MB, データ欠損値: {df_cost_long.isnull().any().sum()}')


if __name__ == "__main__":
    main()
