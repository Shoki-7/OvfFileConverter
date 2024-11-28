import struct
import numpy as np

def read_ovf_file(filename):
    """
    OVFファイルを読み込み、バイナリ形式またはテキスト形式でデータを読み込みます。
    
    Parameters
    ----------
    filename : str
        読み込むOVFファイルの名前
    
    Returns
    -------
    data : np.ndarray
        読み込んだデータを格納したNumPy配列
    headers : dict
        ファイルから取得したヘッダー情報の辞書
    """
    headers = {}
    data = None

    with open(filename, 'rb') as file:
        # ヘッダーを読み込み
        while True:
            line = file.readline().decode('utf-8').strip()
            if line.startswith('#'):
                if 'xnodes' in line:
                    headers['xnodes'] = int(line.split()[-1])
                elif 'ynodes' in line:
                    headers['ynodes'] = int(line.split()[-1])
                elif 'znodes' in line:
                    headers['znodes'] = int(line.split()[-1])
                elif 'valuedim' in line:
                    headers['valuedim'] = int(line.split()[-1])
                elif line.startswith('# Begin: Data'):
                    data_format = line.split()[-1]
                    break  # データセクションに到達
            else:
                raise ValueError("Unexpected file format.")

        # xnodes, ynodes, znodes, valuedim がすべて揃っているか確認
        if not all(k in headers for k in ('xnodes', 'ynodes', 'znodes', 'valuedim')):
            raise ValueError("Incomplete header information.")

        # データの読み込み
        if data_format == '4':
            data = read_binary_data(file, headers)
        elif data_format == 'Text':
            data = read_text_data(file, headers)
        else:
            raise ValueError(f"Unsupported data format: {data_format}")

    return data, headers


def read_binary_data(file, headers):
    """Binary形式でデータを読み込みます"""
    xnodes = headers['xnodes']
    ynodes = headers['ynodes']
    znodes = headers['znodes']
    valuedim = headers['valuedim']

    # OOMMF コントロールナンバーを読み込む（バイナリフォーマット識別用）
    control_number = struct.unpack('<f', file.read(4))[0]
    if control_number != 1234567.0:
        raise ValueError("Invalid OVF control number for Binary format.")

    # データを格納するためのNumPy配列を初期化
    data = np.empty((znodes, ynodes, xnodes, valuedim), dtype=np.float32)

    # データをバイナリ形式で読み込み
    for z in range(znodes):
        for y in range(ynodes):
            for x in range(xnodes):
                data[z, y, x, :] = struct.unpack('<' + 'f' * valuedim, file.read(4 * valuedim))

    return data


def read_text_data(file, headers):
    """Text形式でデータを読み込みます"""
    xnodes = headers['xnodes']
    ynodes = headers['ynodes']
    znodes = headers['znodes']
    valuedim = headers['valuedim']

    # データを格納するためのNumPy配列を初期化
    data = np.empty((znodes, ynodes, xnodes, valuedim), dtype=np.float32)

    # データをテキスト形式で読み込み
    for z in range(znodes):
        for y in range(ynodes):
            for x in range(xnodes):
                line = file.readline().strip().split()
                data[z, y, x, :] = [float(val) for val in line[:valuedim]]

    return data

