import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="Prakiraan Cuaca Kalimantan Tengah", layout="wide")

st.title("🌧️ GFS Viewer Wilayah Kalimantan Tengah (Realtime via NOMADS)")
st.header("Web Hasil Pembelajaran Pengelolaan Informasi Meteorologi")
st.markdown("**Atia Carnesia**  \n*UAS PIM M8TB 2025*")

@st.cache_data
def load_dataset(run_date, run_hour):
    base_url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/gfs{run_date}/gfs_0p25_1hr_{run_hour}z"
    ds = xr.open_dataset(base_url)
    return ds

st.sidebar.title("⚙️ Pengaturan")

# Input pengguna
today = datetime.utcnow()
run_date = st.sidebar.date_input("Tanggal Run GFS (UTC)", today.date())
run_hour = st.sidebar.selectbox("Jam Run GFS (UTC)", ["00", "06", "12", "18"])
forecast_hour = st.sidebar.slider("Jam ke depan", 0, 240, 0, step=1)
parameter = st.sidebar.selectbox("Parameter", [
    "Curah Hujan per jam (pratesfc)",
    "Suhu Permukaan (tmp2m)",
    "Angin Permukaan (ugrd10m & vgrd10m)",
    "Tekanan Permukaan Laut (prmslmsl)"
])

if st.sidebar.button("🔎 Tampilkan Visualisasi"):
    try:
        ds = load_dataset(run_date.strftime("%Y%m%d"), run_hour)
        if forecast_hour >= len(ds.time):
            st.error(f"Data untuk jam ke-{forecast_hour} belum tersedia.")
            st.stop()
        st.success("Dataset berhasil dimuat.")
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        st.stop()

    is_contour = False
    is_vector = False

    # Parameter
    if "pratesfc" in parameter:
        var = ds["pratesfc"][forecast_hour, :, :] * 3600
        label = "Curah Hujan (mm/jam)"
        cmap = "Blues"
        vmin, vmax = 0, 10
    elif "tmp2m" in parameter:
        var = ds["tmp2m"][forecast_hour, :, :] - 273.15
        label = "Suhu (°C)"
        cmap = "coolwarm"
        vmin, vmax = 20, 35
    elif "ugrd10m" in parameter:
        u = ds["ugrd10m"][forecast_hour, :, :]
        v = ds["vgrd10m"][forecast_hour, :, :]
        speed = (u**2 + v**2)**0.5 * 1.94384
        var = speed
        label = "Kecepatan Angin (knot)"
        cmap = plt.cm.get_cmap("RdYlGn_r", 10)
        vmin, vmax = 0, 20
        is_vector = True
    elif "prmsl" in parameter:
        var = ds["prmslmsl"][forecast_hour, :, :] / 100
        label = "Tekanan Permukaan Laut (hPa)"
        cmap = "cool"
        vmin, vmax = 500, 1520
        is_contour = True
    else:
        st.warning("Parameter tidak dikenali.")
        st.stop()

    # Wilayah Kalimantan Tengah diperluas
    lat_min, lat_max = -3.5, 3.0  # Latitude untuk Kalimantan Tengah
    lon_min, lon_max = 113.0, 116.5  # Longitude untuk Kalimantan Tengah
    var = var.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

    if is_vector:
        u = u.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
        v = v.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

    # Plot
    fig = plt.figure(figsize=(10, 7))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    valid_time = ds.time[forecast_hour].values
    valid_dt = pd.to_datetime(str(valid_time))
    valid_str = valid_dt.strftime("%HUTC %a %d %b %Y")
    tstr = f"t+{forecast_hour:03d}"

    ax.set_title(f"{label} • Valid: {valid_str} • GFS {tstr}",
                 fontsize=11, fontweight="bold", loc="center", pad=15)

    if is_contour:
        cs = ax.contour(var.lon, var.lat, var.values, levels=15, colors='black', linewidths=0.8, transform=ccrs.PlateCarree())
        ax.clabel(cs, fmt="%d", colors='black', fontsize=8)
    else:
        im = ax.pcolormesh(var.lon, var.lat, var.values,
                           cmap=cmap, vmin=vmin, vmax=vmax,
                           transform=ccrs.PlateCarree())
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
        cbar.set_label(label)
        if is_vector:
            ax.quiver(var.lon[::1], var.lat[::1],
                      u.values[::1, ::1], v.values[::1, ::1],
                      transform=ccrs.PlateCarree(), scale=500, width=0.002, color='black')

    ax.coastlines(resolution='10m', linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')

    # Titik Palangkaraya (ibu kota Kalimantan Tengah)
    lon_palangka, lat_palangka = 113.9213, -2.2081
    ax.plot(lon_palangka, lat_palangka, marker='o', color='red', markersize=6, transform=ccrs.PlateCarree())
    ax.text(lon_palangka + 0.2, lat_palangka + 0.1, "Palangkaraya", fontsize=9, fontweight='bold', color='black',
            transform=ccrs.PlateCarree(), bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.2'))

    # Titik Observasi Tambahan (Contoh titik lainnya)
    lon_obs, lat_obs = 114.907933, -1.682540
    ax.plot(lon_obs, lat_obs, marker='^', color='blue', markersize=6, transform=ccrs.PlateCarree())
    ax.text(lon_obs + 0.2, lat_obs - 0.2, "Obs Point", fontsize=9, fontweight='bold', color='blue',
            transform=ccrs.PlateCarree(), bbox=dict(facecolor='white', edgecolor='blue', boxstyle='round,pad=0.2'))

    st.pyplot(fig)

    # Download tombol
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    st.download_button("📥 Download Gambar", buf.getvalue(), file_name="gfs_kalimantan_tengah.png", mime="image/png")
