# PingPong_tracker
Tracks ball of ping pong via vision via a particle filter framework more specifically via the [**Condensation algorithm**](https://en.wikipedia.org/wiki/Condensation_algorithm).
## Frames from video
The first important task to solve is to retrieve the "raw" pictures from a video e.g. from a .mp4. Additionally, it is extremely beneficial for the filter to know the exact timestamp of those pictures. To accomplish those tasks the functionality of ffmpeg and ffprobe under Linux are leveraged. If you execute the file `frames_from_video.sh` from the command line (make sure file is executable) all images of the video are extracted and stored as .png. On top of that the pts and dts timestamps are stored in the file timestamps.json. `pts` is an acronym for presentation time stamp and `dts` is an acronym for decoder time stamp. Both are extracted but actually only the pts timestamps are relevant later in the filter framework. To extract frames and timestamps of a video, type the following:

`./frames_from_video.sh <video> <folder to store frames and time stamps>`
## Selection of target histogram
The image below shows the histogram of the ball and some surrounding.   
![histogram](images_README/histogram.png)
## Computation of measurement update
Every update step of the particle filter procedure involves the weighing of every single particle. This weighing is accomplished by computing the histogram within a rectangle around the particles center point and then comparing with the target histogram. As a comparison measure the so-called [**Hellinger distance**](https://en.wikipedia.org/wiki/Hellinger_distance) is selected. The **Hellinger distance** is related to the famous Bhattacharyya coefficient and computed as follows:

<a href="https://www.codecogs.com/eqnedit.php?latex=d_{hellinger}(p^*,p(\vec{x_t}))&space;=&space;\sqrt{1&space;-&space;\sum_{j=1}^{m}&space;\sqrt{p_u^*(\vec{x_0})p_u(\vec{x_t})}}&space;\newline&space;\vec{x_0}:=&space;\text{States&space;of&space;target}&space;\newline&space;\vec{x_t}:=&space;\text{States&space;of&space;particle&space;t}&space;\newline&space;p_u^*(\vec{x_0}):=\text{Normalized&space;number&space;of&space;intensity&space;values&space;of&space;target&space;measurement&space;rectangle&space;that&space;lie&space;in&space;bin&space;\textit{u}}&space;\newline&space;p_u(\vec{x_t}):=\text{Normalized&space;number&space;of&space;intensity&space;values&space;of&space;particel&space;\textit{t}'s&space;measurement&space;rectangle&space;that&space;lie&space;in&space;bin&space;\textit{u}}&space;\newline&space;m:=\text{Number&space;of&space;bins&space;of&space;histograms}" target="_blank"><img src="https://latex.codecogs.com/gif.latex?d_{hellinger}(p^*,p(\vec{x_t}))&space;=&space;\sqrt{1&space;-&space;\sum_{j=1}^{m}&space;\sqrt{p_u^*(\vec{x_0})p_u(\vec{x_t})}}&space;\newline&space;\vec{x_0}:=&space;\text{States&space;of&space;target}&space;\newline&space;\vec{x_t}:=&space;\text{States&space;of&space;particle&space;t}&space;\newline&space;p_u^*(\vec{x_0}):=\text{Normalized&space;number&space;of&space;intensity&space;values&space;of&space;target&space;measurement&space;rectangle&space;that&space;lie&space;in&space;bin&space;\textit{u}}&space;\newline&space;p_u(\vec{x_t}):=\text{Normalized&space;number&space;of&space;intensity&space;values&space;of&space;particel&space;\textit{t}'s&space;measurement&space;rectangle&space;that&space;lie&space;in&space;bin&space;\textit{u}}&space;\newline&space;m:=\text{Number&space;of&space;bins&space;of&space;histograms}" title="d_{hellinger}(p^*,p(\vec{x_t})) = \sqrt{1 - \sum_{j=1}^{m} \sqrt{p_u^*(\vec{x_0})p_u(\vec{x_t})}} \newline \vec{x_0}:= \text{States of target} \newline \vec{x_t}:= \text{States of particle t} \newline p_u^*(\vec{x_0}):=\text{Normalized number of intensity values of target measurement rectangle that lie in bin \textit{u}} \newline p_u(\vec{x_t}):=\text{Normalized number of intensity values of particel \textit{t}'s measurement rectangle that lie in bin \textit{u}} \newline m:=\text{Number of bins of histograms}" /></a>

 The **Hellinger distance** takes values between 0 and 1. It takes 0 if there is perfect overlap and 1 if there is no overlap at all for the two distributions or in this case for the two discrete histograms. The figures below show how the value for the Hellinger distance behaves for the different pairwise fictional normal distribution. Both distributions have the same standard deviation but different mean values expect for the first plot where both entities are the same. The bigger the average shifts the closer the Hellinger distance goes to 1.
![hellinger](images_README/hellinger_hist.png)

If you want to play around with the different mean shift values or standard deviations or even different distribution like laplace you can do that by manipulating `distribution_comparison.py` accordingly. As mentioned in the equation the input for the computation of the Hellinger distance are the normalized bin counts i.e. 

<a href="https://www.codecogs.com/eqnedit.php?latex=p_u(\vec{x_t})=&space;\frac{n_u(\vec{x_t})}{\sum_{j=1}^m&space;n_j(\vec{x_t}))}\newline&space;n_u:=&space;\text{Bin&space;count&space;of&space;bin&space;\textit{u}}" target="_blank"><img src="https://latex.codecogs.com/gif.latex?p_u(\vec{x_t})=&space;\frac{n_u(\vec{x_t})}{\sum_{j=1}^m&space;n_j(\vec{x_t}))}\newline&space;n_u:=&space;\text{Bin&space;count&space;of&space;bin&space;\textit{u}}" title="p_u(\vec{x_t})= \frac{n_u(\vec{x_t})}{\sum_{j=1}^m n_j(\vec{x_t}))}\newline n_u:= \text{Bin count of bin \textit{u}}" /></a>