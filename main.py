import calendar
import datetime
import pandas as pd
import streamlit as st


def get_year_month_from_file(file):
    # ファイル名から年月文字列を取得
    file_name = file.name.split('.')[0].split('_')[-1]
    return file_name


def get_end_of_month_date(str_yyyymm):
    # ファイル名から月末日付を取得
    year = int(str_yyyymm[:4])
    month = int(str_yyyymm[-2:])
    last_day = calendar.monthrange(year, month)[1]

    eom = datetime.date(year, month, last_day).strftime('%Y/%m/%d')
    return eom


def get_df_info(df):
    # データフレームからファイル容量、サイズ、欠損値の有無を取得
    data_shape = df.shape
    data_size = df.memory_usage().sum()
    count_null = df.isnull().any().sum()

    return data_shape, data_size, count_null


@st.cache
def load_file(file):
    df = pd.read_csv(file, encoding='cp932')
    return df


# --- 仕訳データの変換処理 ----
def filtered_df(df):
    # 並び替えとカラムの整理、リネーム

    # カラム名変更用辞書（一次処理）
    dict_account_conversion = {
        '借方科目コード': 'dr_cd',
        '借方科目名称': 'dr_name',
        '借方科目別補助コード': 'dr_sub_cd',
        '借方科目別補助名称': 'dr_sub_name',
        '借方部門コード': 'dr_section_cd',
        '借方部門名称': 'dr_section_name',
        '借方セグメント2': 'dr_segment_cd',
        '借方セグメント２名称': 'dr_segment_name',
        '貸方科目コード': 'cr_cd',
        '貸方科目名称': 'cr_name',
        '貸方科目別補助コード': 'cr_sub_cd',
        '貸方科目別補助名称': 'cr_sub_name',
        '貸方部門コード': 'cr_section_cd',
        '貸方部門名称': 'cr_section_name',
        '貸プセグメント2コード': 'cr_segment_cd',
        '貸方セグメント２名称': 'cr_segment_name',
        '金額': 'price',
        '消費税': 'tax',
        '摘要': 'outline'
    }

    df = df.filter(
            ['借方科目コード', '借方科目名称', '借方科目別補助コード', '借方科目別補助名称', '借方部門コード', '借方部門名称',
             '借方セグメント2', '借方セグメント２名称', '貸方科目コード', '貸方科目名称', '貸方科目別補助コード', '貸方科目別補助名称',
             '貸方部門コード', '貸方部門名称', '貸プセグメント2コード', '貸方セグメント２名称', '金額', '消費税', '摘要'])\
        .rename(dict_account_conversion, axis=1)

    return df


def convert_df(file):
    # データの読み込み
    df = load_file(file)
    # 必要なカラムのフィルタリングとコード変換
    filtered = filtered_df(df)
    return filtered


# -- 借方データの整形処理 --
def convert_dr(df):
    df = df.copy().assign(price=lambda x: df['price'] - df['tax']).drop('tax', axis=1)

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
    df = df.copy().assign(price=lambda x: df['price'] - df['tax']).drop('tax', axis=1)

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
def concat_df(dr, cr):
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
    df = df.fillna(0)
    df.dropna(subset='金額', inplace=True)
    df['科目CD'] = df['科目CD'].apply(lambda x: str(int(x)))
    df['補助科目CD'] = df['補助科目CD'].apply(lambda x: str(int(x)))
    df['部門CD'] = df['部門CD'].apply(lambda x: str(int(x)))

    return df


@st.cache
def convert_to_csv(df, index=False):
    return df.to_csv(index=False).encode('cp932')


def main():
    """
    Streamlit Main Application
    :return:
    """

    # ヘッダーセクション
    st.title('仕訳データの分析用変換ツール')
    st.caption('振替伝票仕訳データを使った、データ分析用コード変換処理')

    # サイドバーセクション
    side_header = st.sidebar.container()
    side_header.write('--FILE UPLOADER--')
    side_header.write('#### 1.振替伝票 → 単票形式')
    side_header.caption('複式簿記形式 → 単票形式への組み換え')

    uploaded_file = side_header.file_uploader('ファイル名：◯◯◯◯_YYYYMM', type='csv')

    side_header.write('---')

    side_header.write('#### 2.配賦データ → 縦変換')
    side_header.caption('各セグメントへ配賦した横データ(wide)を縦型(long)に組み換え')

    flg_box = side_header.radio('予算/実績の区分を選択', ('実績', '予算'))
    uploaded_wide_file = side_header.file_uploader('ファイル名: ◯◯◯◯_YYYYMM', type='csv')

    # メインセクション
    container_main = st.container()
    container_main.write('---')

    # １次処理用
    if uploaded_file is not None:
        # データの読み込み
        df = convert_df(uploaded_file)

        # 借方データの整形処理
        df_dr = calc_dr(df)

        # 貸方データの整形処理
        df_cr = calc_cr(df)

        # 貸借データの縦連結
        df_concat = concat_df(df_dr, df_cr)
        concat_data_shape, concat_data_size, concat_count_null = get_df_info(df_concat)

        # 人件費に関するコードリスト
        labor_cost_cd_list = [
            '6110', '6120', '6130', '6140', '6150', '6160', '6170', '6180', '6190', '6200',
            '7110', '7120', '7130', '7140', '7150', '7160', '7170', '7180', '7190', '7200'
        ]

        # ac_cdからlabor_cost_cd_listにないものだけをリスト化
        value_list = list(set(df_concat['ac_cd'].values))
        target_list = sorted([item for item in value_list if item not in labor_cost_cd_list])

        # 人件費項目を除外したデータフレームを作成
        df_exclude_labor_cost = df_concat.query('ac_cd in @target_list')
        exc_data_shape, exc_data_size, exc_count_null = get_df_info(df_exclude_labor_cost)

        container_main.subheader('1-1. Result - Details')

        show_detail = container_main.checkbox('Check & Preview - Details!')

        if show_detail:
            container_main.dataframe(df_concat, use_container_width=True)

        output_result_detail = convert_to_csv(df_concat, index=False)

        container_main.download_button(
            label='DL: 詳細データ',
            data=output_result_detail,
            file_name=f'result_detail_{get_year_month_from_file(uploaded_file)}.csv',
            mime='text/csv'
        )
        container_main.caption(
            f'参考）サイズ: {concat_data_shape},　容量: {concat_data_size / 1024:.1f} MB, データ欠損値: {concat_count_null}')

        container_main.write('---')
        # 人件費科目を除外したデータの処理
        output_result_exclude_labor_cost = convert_to_csv(df_exclude_labor_cost, index=False)

        show_detail_exclude = container_main.checkbox('Check & Preview - Exclude Labor Cost')

        if show_detail_exclude:
            container_main.dataframe(df_exclude_labor_cost, use_container_width=True)

        container_main.download_button(
            label='DL: 詳細(人件費除き)',
            data=output_result_exclude_labor_cost,
            file_name=f'result_exclude_labor_cost_{get_year_month_from_file(uploaded_file)}.csv',
            mime='text/csv'
        )
        container_main.caption(
            f'参考）サイズ: {exc_data_shape},　容量: {exc_data_size / 1024:.1f} MB, データ欠損値: {exc_count_null}')


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
            file_name=f'result_{get_year_month_from_file(uploaded_file)}.csv',
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
            df['期間'] = get_end_of_month_date(get_year_month_from_file(uploaded_wide_file))

        elif flg_box == '予算':
            df['予算/実績'] = '予算'
            df['期間'] = get_end_of_month_date(get_year_month_from_file(uploaded_wide_file))

        else:
            df['予算/実績'] = ''
            df['期間'] = get_end_of_month_date(get_year_month_from_file(uploaded_wide_file))

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
            file_name=f'result_sales_long_{get_year_month_from_file(uploaded_wide_file)}.csv',
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
            file_name=f'result_cost_long_{get_year_month_from_file(uploaded_wide_file)}.csv',
            mime='text/csv'
        )
        container_main.caption(
            f'参考）サイズ: {df_cost_long.shape},　容量: {data_size / 1024:.1f} MB, データ欠損値: {df_cost_long.isnull().any().sum()}')


if __name__ == "__main__":
    main()
